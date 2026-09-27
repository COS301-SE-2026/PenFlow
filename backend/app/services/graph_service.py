from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.base import Severity
from app.models.detected_technology import DetectedTechnology
from app.models.finding import Finding
from app.models.scan import Scan
from app.models.service import Service
from app.models.user import User
from app.repositories.scan_repo import ScanRepository
from app.schemas.graph import (
    GraphChangedValue,
    GraphCompareResponse,
    GraphConcentration,
    GraphEdge,
    GraphEdgeProvenance,
    GraphFindingSummary,
    GraphNeighborhoodResponse,
    GraphNode,
    GraphNodeChange,
    GraphNodeDetailResponse,
    GraphNodeRelationshipCounts,
    GraphPath,
    GraphPathsResponse,
    GraphResponse,
    GraphRisk,
    GraphSummaryCounts,
    GraphSummaryResponse,
    GraphSummaryRisk,
)
from app.services.scan_delta_service import (
    extract_target_identity,
    normalize_source,
    normalize_text,
)

_SEVERITY_ORDER= {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}

class _GraphData:
    def __init__(self) -> None:
        self.nodes: list[GraphNode] = []
        self.edges: list[GraphEdge] = []
        self.findings_by_node: dict[str, list[Finding]] = {}
        #DB UUID differs between scans. Used by compare_scans
        self.logical_key: dict[str, str] = {}

def _risk_from_findings(findings: list[Finding]) ->GraphRisk:
    if not findings:
        return GraphRisk(severity=None, max_cvss=None, finding_count=0)

    worst = max(findings, key=lambda f: _SEVERITY_ORDER[f.severity])
    cvss_values = [float(f.cvss_score) for f in findings if f.cvss_score is not None]

    return GraphRisk(
        severity=worst.severity.value,
        max_cvss=max(cvss_values) if cvss_values else None,
        finding_count=len(findings),
    )

def _finding_identity(finding: Finding, asset_identifier: str | None) -> str:
    parts = [
        normalize_source(finding.source),
        normalize_text(finding.cve_id),
        normalize_text(finding.title),
        normalize_text(asset_identifier),
        extract_target_identity(finding.evidence),
    ]
    return "::".join(parts)

class GraphService:
    @staticmethod
    async def require_scan_access(
        db: AsyncSession,
        scan_id: UUID,
        user: User,
    ) -> Scan:
        scan = await ScanRepository.get_scan_by_id(db, scan_id)

        if scan is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan not found.",
            )

        is_owner = scan.user_id is not None and scan.user_id == user.id
        if not is_owner and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan not found.",
            )

        return scan
    #core engine all endpoint call this function
    @staticmethod
    async def _load_graph_data(db: AsyncSession, scan: Scan) -> _GraphData:
        #fetch raw data
        assets = (
            await db.execute(select(Asset).where(Asset.scan_id == scan.id))
        ).scalars().all()
        services = (
            await db.execute(select(Service).where(Service.scan_id == scan.id))
        ).scalars().all()
        technologies = (
            await db.execute(
                select(DetectedTechnology).where(DetectedTechnology.scan_id == scan.id)
            )
        ).scalars().all()
        findings = (
            await db.execute(select(Finding).where(Finding.scan_id == scan.id))
        ).scalars().all()
        #set up container and index findings
        data = _GraphData()

        findings_by_asset: dict[UUID, list[Finding]] = {}
        findings_by_service: dict[UUID, list[Finding]] = {}
        for f in findings:
            if f.asset_id is not None:
                findings_by_asset.setdefault(f.asset_id, []).append(f)
            if f.service_id is not None:
                findings_by_service.setdefault(f.service_id, []).append(f)

        #create domain node
        domain_id = f"domain:{scan.domain}"
        domain_findings = list(findings)
        data.nodes.append(
            GraphNode(
                id=domain_id,
                entity_id=None,
                type="domain",
                label=scan.domain,
                risk=_risk_from_findings(domain_findings),
                metadata={},
            )
        )
        data.findings_by_node[domain_id] = domain_findings
        data.logical_key[domain_id] = f"domain:{normalize_text(scan.domain)}"
        #Build asset nodes and their domain edges
        asset_identifier_by_id: dict[UUID, str] = {a.id: a.identifier for a in assets}

        asset_node_id: dict[UUID, str] ={}
        for a in assets:
            node_id = f"asset:{a.id}"
            asset_node_id[a.id] = node_id
            asset_findings = findings_by_asset.get(a.id,[])
            data.nodes.append(
                GraphNode(
                    id=node_id,
                    entity_id=a.id,
                    type="asset",
                    label=a.identifier,
                    risk=_risk_from_findings(asset_findings),
                    metadata={"asset_type": a.asset_type, **(a.asset_metadata or {})},
                )
            )
            data.findings_by_node[node_id] = asset_findings
            data.logical_key[node_id] = (
                f"asset:{normalize_text(a.identifier)}|{normalize_text(a.asset_type)}"
            )
            data.edges.append(
                GraphEdge(
                    id=f"resolves-to:{scan.domain}:{a.id}",
                    source=domain_id,
                    target=node_id,
                    type="RESOLVES_TO",
                    provenance=GraphEdgeProvenance(
                        source="scan",
                        observed_at=a.created_at,
                        confidence=1.0,
                    ),
                )
            )

        #build service node
            service_node_id: dict[UUID, str] = {}
        for s in services:
            node_id = f"service:{s.id}"
            service_node_id[s.id] = node_id
            service_findings = findings_by_service.get(s.id,[])
            data.nodes.append(
                GraphNode(
                    id=node_id,
                    entity_id=s.id,
                    type="service",
                    label=f"{(s.service_name or s.protocol).upper()} :{s.port}",
                    risk=_risk_from_findings(service_findings),
                    metadata={
                        "host": s.host,
                        "port": s.port,
                        "protocol": s.protocol,
                        "product": s.product,
                        "version": s.version,
                        "tls_enabled": s.tls_enabled,
                        "state": s.state,
                    },
                )
            )
            data.findings_by_node[node_id] = service_findings
            data.logical_key[node_id] = (
                f"service:{normalize_text(s.host)}:{s.port}/{normalize_text(s.protocol)}"
            )

            if s.asset_id is not None and s.asset_id in asset_node_id:
                data.edges.append(
                    GraphEdge(
                        id=f"exposes:{s.asset_id}:{s.id}",
                        source=asset_node_id[s.asset_id],
                        target=node_id,
                        type="EXPOSES",
                        provenance=GraphEdgeProvenance(
                            source="nmap",
                            observed_at=s.created_at,
                            confidence=1.0,
                        ),
                    )
                )

        for t in technologies:
            node_id = f"technology:{t.id}"
            data.nodes.append(
                GraphNode(
                    id=node_id,
                    entity_id=t.id,
                    type="technology",
                    label=f"{t.product} {t.version}".strip() if t.version else t.product,
                    risk=GraphRisk(severity=None, max_cvss=None, finding_count=0),
                    metadata={
                        "technology_type": t.technology_type,
                        "detection_source": t.detection_source,
                        "confidence": float(t.confidence) if t.confidence is not None else None,
                    },
                )
            )
            data.findings_by_node[node_id] = []

            # fall back to the asset.
            parent_node_id = None
            if t.service_id is not None and t.service_id in service_node_id:
                parent_node_id = service_node_id[t.service_id]
            elif t.asset_id is not None and t.asset_id in asset_node_id:
                parent_node_id = asset_node_id[t.asset_id]

            data.logical_key[node_id] = (
                f"technology:{normalize_text(t.product)}|{normalize_text(t.version)}|"
                f"{normalize_text(t.technology_type)}|"
                f"{data.logical_key.get(parent_node_id, '') if parent_node_id else ''}"
            )

            if parent_node_id is not None:
                data.edges.append(
                    GraphEdge(
                        id=f"runs:{parent_node_id}:{t.id}",
                        source=parent_node_id,
                        target=node_id,
                        type="RUNS",
                        provenance=GraphEdgeProvenance(
                            source=t.detection_source or "fingerprint",
                            observed_at=t.created_at,
                            confidence=float(t.confidence) if t.confidence is not None else None,
                        ),
                    )
                )

        for f in findings:
            node_id = f"finding:{f.id}"
            data.nodes.append(
                GraphNode(
                    id=node_id,
                    entity_id=f.id,
                    type="finding",
                    label=f.title,
                    risk=_risk_from_findings([f]),
                    metadata={"cve_id": f.cve_id, "status": f.status.value},
                )
            )
            data.findings_by_node[node_id] = [f]
            data.logical_key[node_id] = (
                f"finding:{_finding_identity(f, asset_identifier_by_id.get(f.asset_id))}"
            )

            # Findings attach to whichever node is most specific; there is no
            # technology to finding link in the schema, so we don't invent one.
            parent_node_id = None
            if f.service_id is not None and f.service_id in service_node_id:
                parent_node_id = service_node_id[f.service_id]
            elif f.asset_id is not None and f.asset_id in asset_node_id:
                parent_node_id = asset_node_id[f.asset_id]

            if parent_node_id is not None:
                data.edges.append(
                    GraphEdge(
                        id=f"affected-by:{parent_node_id}:{f.id}",
                        source=parent_node_id,
                        target=node_id,
                        type="AFFECTED_BY",
                        provenance=GraphEdgeProvenance(
                            source=f.source,
                            observed_at=f.created_at,
                            confidence=1.0 if f.is_verified else None,
                        ),
                    )
                )

        return data
    
    @staticmethod
    async def get_graph(db: AsyncSession, scan: Scan) -> GraphResponse:
        data = await GraphService._load_graph_data(db, scan)
        return GraphResponse(
            scan_id=scan.id,
            domain=scan.domain,
            generated_at=datetime.now(timezone.utc),
            nodes=data.nodes,
            edges=data.edges,
        )

    @staticmethod
    async def get_node(
        db: AsyncSession, scan: Scan, node_id: str
    ) -> GraphNodeDetailResponse:
        data = await GraphService._load_graph_data(db, scan)

        node = next((n for n in data.nodes if n.id == node_id), None)
        if node is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Graph node not found.",
            )

        incoming = sum(1 for e in data.edges if e.target == node_id)
        outgoing = sum(1 for e in data.edges if e.source == node_id)

        findings = [
            GraphFindingSummary(
                id=f.id,
                title=f.title,
                severity=f.severity.value,
                cvss_score=float(f.cvss_score) if f.cvss_score is not None else None,
                cve_id=f.cve_id,
                status=f.status.value,
            )
            for f in data.findings_by_node.get(node_id, [])
        ]

        provenance = [e.provenance for e in data.edges if e.target == node_id]

        return GraphNodeDetailResponse(
            node=node,
            relationships=GraphNodeRelationshipCounts(incoming=incoming, outgoing=outgoing),
            findings=findings,
            provenance=provenance,
        )
    @staticmethod
    async def get_summary(db: AsyncSession, scan: Scan) -> GraphSummaryResponse:
        data = await GraphService._load_graph_data(db, scan)

        counts_by_type: dict[str, int] = {}
        for n in data.nodes:
            counts_by_type[n.type] = counts_by_type.get(n.type, 0) + 1

        all_findings = data.findings_by_node.get(f"domain:{scan.domain}", [])
        severity_counts = dict.fromkeys(("critical", "high", "medium", "low"), 0)
        for f in all_findings:
            if f.severity.value in severity_counts:
                severity_counts[f.severity.value] += 1

        affected_assets = sum(
            1 for n in data.nodes if n.type == "asset" and n.risk.finding_count > 0
        )

        ranked = sorted(
            (n for n in data.nodes if n.type != "domain" and n.risk.severity is not None),
            key=lambda n: (_SEVERITY_ORDER[Severity(n.risk.severity)], n.risk.max_cvss or 0),
            reverse=True,
        )
        highest_risk_node_id = ranked[0].id if ranked else None

        concentration_candidates = [
            n for n in data.nodes if n.type in ("asset", "service") and n.risk.finding_count > 0
        ]
        concentration_candidates.sort(key=lambda n: n.risk.finding_count, reverse=True)

        concentrations = []
        for n in concentration_candidates[:5]:
            node_findings = data.findings_by_node.get(n.id, [])
            critical_count = sum(1 for f in node_findings if f.severity == Severity.CRITICAL)
            high_count = sum(1 for f in node_findings if f.severity == Severity.HIGH)
            concentrations.append(
                GraphConcentration(
                    node_id=n.id,
                    label=n.label,
                    finding_count=n.risk.finding_count,
                    critical_count=critical_count,
                    high_count=high_count,
                    max_cvss=n.risk.max_cvss,
                )
            )

        return GraphSummaryResponse(
            scan_id=scan.id,
            counts=GraphSummaryCounts(
                domains=counts_by_type.get("domain", 0),
                assets=counts_by_type.get("asset", 0),
                services=counts_by_type.get("service", 0),
                technologies=counts_by_type.get("technology", 0),
                findings=counts_by_type.get("finding", 0),
                edges=len(data.edges),
            ),
            risk=GraphSummaryRisk(
                critical_findings=severity_counts["critical"],
                high_findings=severity_counts["high"],
                medium_findings=severity_counts["medium"],
                low_findings=severity_counts["low"],
                affected_assets=affected_assets,
                highest_risk_node_id=highest_risk_node_id,
            ),
            concentrations=concentrations,
        )

    @staticmethod
    async def get_paths(
        db: AsyncSession,
        scan: Scan,
        *,
        severity: str | None = None,
        finding_id: UUID | None = None,
        asset_id: UUID | None = None,
        limit: int = 10,
    ) -> GraphPathsResponse:
        data = await GraphService._load_graph_data(db, scan)

        #each node can only have 1 parent
        #1 edge pointing up to each container
        #graph is a set of trees with no loop mean
        #tracking a domainn is a simple walk upwards
        predecessor: dict[str, GraphEdge] = {e.target: e for e in data.edges}

        finding_nodes = [n for n in data.nodes if n.type == "finding"]

        if severity is not None:
            min_rank = _SEVERITY_ORDER[Severity(severity)]
            finding_nodes = [
                n for n in finding_nodes
                if n.risk.severity is not None
                and _SEVERITY_ORDER[Severity(n.risk.severity)] >= min_rank
            ]

        if finding_id is not None:
            finding_nodes = [n for n in finding_nodes if n.entity_id == finding_id]

        finding_nodes.sort(
            key=lambda n: (
                _SEVERITY_ORDER[Severity(n.risk.severity)] if n.risk.severity else -1,
                n.risk.max_cvss or 0,
            ),
            reverse=True,
        )

        paths: list[GraphPath] = []
        for n in finding_nodes:
            path_node_ids = [n.id]
            path_edge_ids: list[str] = []
            current = n.id
            while current in predecessor:
                edge = predecessor[current]
                path_edge_ids.append(edge.id)
                path_node_ids.append(edge.source)
                current = edge.source
            path_node_ids.reverse()
            path_edge_ids.reverse()

            if asset_id is not None:
                asset_node_id = f"asset:{asset_id}"
                if asset_node_id not in path_node_ids:
                    continue

            paths.append(
                GraphPath(
                    id=f"risk-path-{len(paths) + 1}",
                    risk=n.risk,
                    nodes=path_node_ids,
                    edges=path_edge_ids,
                )
            )

            if len(paths) >= limit:
                break

        return GraphPathsResponse(paths=paths)

    @staticmethod
    async def get_neighborhood(
        db: AsyncSession,
        scan: Scan,
        node_id: str,
        *,
        depth: int = 2,
    ) -> GraphNeighborhoodResponse:
        data = await GraphService._load_graph_data(db, scan)

        if not any(n.id == node_id for n in data.nodes):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Graph node not found.",
            )

        adjacency: dict[str, list[str]] = {}
        for e in data.edges:
            adjacency.setdefault(e.source, []).append(e.target)
            adjacency.setdefault(e.target, []).append(e.source)

        visited = {node_id}
        frontier = {node_id}
        for _ in range(depth):
            next_frontier: set[str] = set()
            for nid in frontier:
                for neighbor in adjacency.get(nid, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_frontier.add(neighbor)
            if not next_frontier:
                break
            frontier = next_frontier

        neighborhood_nodes = [n for n in data.nodes if n.id in visited]
        neighborhood_edges = [
            e for e in data.edges if e.source in visited and e.target in visited
        ]

        return GraphNeighborhoodResponse(
            root_node_id=node_id,
            depth=depth,
            nodes=neighborhood_nodes,
            edges=neighborhood_edges,
        )

    #compare scan method
    @staticmethod
    async def compare_scans(
        db: AsyncSession,
        current_scan: Scan,
        previous_scan: Scan,
    ) -> GraphCompareResponse:
        if normalize_text(current_scan.domain) != normalize_text(previous_scan.domain):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Scans are for different domains and are not comparable.",
            )

        current = await GraphService._load_graph_data(db, current_scan)
        previous = await GraphService._load_graph_data(db, previous_scan)

        current_by_key = {current.logical_key[n.id]: n for n in current.nodes}
        previous_by_key = {previous.logical_key[n.id]: n for n in previous.nodes}

        current_keys = set(current_by_key)
        previous_keys = set(previous_by_key)

        added_nodes = [current_by_key[k].id for k in sorted(current_keys - previous_keys)]
        removed_nodes = [previous_by_key[k].id for k in sorted(previous_keys - current_keys)]

        changed_nodes: list[GraphNodeChange] = []
        for key in sorted(current_keys & previous_keys):
            current_node = current_by_key[key]
            previous_node = previous_by_key[key]
            changes: dict[str, GraphChangedValue] = {}

            if current_node.risk.finding_count != previous_node.risk.finding_count:
                changes["finding_count"] = GraphChangedValue(
                    previous=previous_node.risk.finding_count,
                    current=current_node.risk.finding_count,
                )

            if current_node.risk.severity != previous_node.risk.severity:
                changes["severity"] = GraphChangedValue(
                    previous=previous_node.risk.severity,
                    current=current_node.risk.severity,
                )

            if changes:
                changed_nodes.append(GraphNodeChange(node_id=key, changes=changes))

        def _edge_key(edge: GraphEdge, logical_key: dict[str, str]) -> str:
            return f"{edge.type}:{logical_key[edge.source]}->{logical_key[edge.target]}"

        current_edge_by_key = {
            _edge_key(e, current.logical_key): e for e in current.edges
        }
        previous_edge_by_key = {
            _edge_key(e, previous.logical_key): e for e in previous.edges
        }

        added_edges = [
            current_edge_by_key[k].id
            for k in sorted(set(current_edge_by_key) - set(previous_edge_by_key))
        ]
        removed_edges = [
            previous_edge_by_key[k].id
            for k in sorted(set(previous_edge_by_key) - set(current_edge_by_key))
        ]

        current_findings = current.findings_by_node.get(f"domain:{current_scan.domain}", [])
        previous_findings = previous.findings_by_node.get(
            f"domain:{previous_scan.domain}", []
        )

        risk_change = {
            "critical_findings": GraphChangedValue(
                previous=sum(1 for f in previous_findings if f.severity == Severity.CRITICAL),
                current=sum(1 for f in current_findings if f.severity == Severity.CRITICAL),
            ),
            "high_findings": GraphChangedValue(
                previous=sum(1 for f in previous_findings if f.severity == Severity.HIGH),
                current=sum(1 for f in current_findings if f.severity == Severity.HIGH),
            ),
        }

        return GraphCompareResponse(
            current_scan_id=current_scan.id,
            previous_scan_id=previous_scan.id,
            added_nodes=added_nodes,
            removed_nodes=removed_nodes,
            changed_nodes=changed_nodes,
            added_edges=added_edges,
            removed_edges=removed_edges,
            risk_change=risk_change,
        )