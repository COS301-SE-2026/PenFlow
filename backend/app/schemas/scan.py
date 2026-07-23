from datetime import datetime
from typing import Any
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.base import ScanStatus

class ScanTypeEnum(str, Enum):
    PASSIVE_CTEM = "passive_ctem"
    ACTIVE_VULNERABILITY = "active_vulnerability"


class InitiateScanRequest(BaseModel):
    domain: str = Field(...,description="The target domain to scan", json_schema_extra={"example": "exmpl.com"}) # noqa: E501
    scan_type: ScanTypeEnum = Field(default=ScanTypeEnum.PASSIVE_CTEM, description="Type of scan to perform")
    verified_domain_id: UUID | None = Field(default=None, description="Required for active scans")
    email: EmailStr | None = Field(None,description="email to send the report to")

class InitiateScanResponse(BaseModel):
    scan_id: UUID
    status: ScanStatus

class ScanCallbackRequest(BaseModel):
    status: ScanStatus
    error_message: str | None = None

class ScanHistoryItem(BaseModel):
    id: UUID
    domain: str
    created_at: datetime
    status: ScanStatus
    scan_type: ScanTypeEnum
    progress: int
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int

    model_config = ConfigDict(from_attributes=True)


class ScanSourceCallbackRequest(BaseModel):
    status: str
    raw_result: dict[str, Any] | None = None
    findings: list[dict[str, Any]] = []
    assets: list[dict[str, Any]] = []
    error_message: str | None = None

class FindingsCount(BaseModel):
    critical: int
    high: int
    medium: int
    low: int
    info: int
    total: int

class MetricsResponse(BaseModel):
    risk_score: int
    risk_level: str
    findings: FindingsCount
    assets: dict[str, int]
    services: dict[str, int]
    technologies: dict[str, int]

class DashboardFindingItem(BaseModel):
    id: UUID
    title: str
    cve_id: str | None = None
    severity: str
    cvss_score: float | None = None
    source: str
    asset_identifier: str | None = None
    description: str | None = None
    recommendation: str | None = None

class DashboardAssetItem(BaseModel):
    id: UUID
    identifier: str
    asset_type: str
    findings_count: int

class RiskHistoryItem(BaseModel):
    date: str
    risk_score: int
    total_findings: int

class FindingSeverityCounts(BaseModel):
    critical: int
    high:int
    medium: int
    low_info: int
    total: int

class FindingListResponse(BaseModel):
    total: int
    counts: FindingSeverityCounts
    items: list[dict[str, Any]]