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