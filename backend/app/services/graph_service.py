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
   