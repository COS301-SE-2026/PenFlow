from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.base import Severity


class ScanSummary(BaseModel):
    id: UUID
    domain: str
    status: str
    progress: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class RiskSnapshot(BaseModel):
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0

class TopFindingPreview(BaseModel):
    id: UUID
    severity: Sevrity
    title: str
    description: Optional[str] = None
    recommendation: Optional[str] = None
    source: str
    asset_identifier: Optional[str] = None
    asset_type: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AssetTypeBreakdown(BaseModel):
    asset_type: str
    total_assests: int
    affected_assets: int

class TopAffectedAsset(BaseModel):
    identifier: str
    asset_type: str
    finding_count: int
    highest_severity: Severity

class AssetImpactSummary(BaseModel):
    total_assets_scanned: int
    afffected_assets_count: int
    asset_type_breakdown: list[AssetTypeBreakdown]
    top_affected_assets: list[TopAffectedAsset]

class ExecutiveSummary(BaseModel):
    scan_summary: ScanSummary
    risk_snapshot: RiskSnapshot
    top_findings: list[TopFindingPreview]
    asset_impact: AssetImpactSummary