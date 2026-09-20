from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SecurityPriorityFinding(BaseModel):
    finding_id: UUID
    priority: int = Field(ge=1)
    title: str
    severity: str
    cvss_score: float | None
    status: str
    is_verified: bool
    priority_reasons: list[str] = Field(
        min_length=1,
    )
    content: str


class SecurityExactFinding(BaseModel):
    finding_id: UUID
    title: str
    severity: str
    cvss_score: float | None
    cve_id: str | None
    status: str
    is_verified: bool
    match_reason: str
    content: str


class SecurityExactLookupResult(BaseModel):
    identifier_type: Literal[
        "finding_id",
        "cve",
    ] | None
    identifier_value: str | None
    findings: list[SecurityExactFinding] = Field(
        default_factory=list,
    )


class SecurityComparisonFinding(BaseModel):
    finding_id: UUID
    scan_id: UUID
    previous_finding_id: UUID | None = None
    change: Literal[
        "new",
        "persistent",
        "no_longer_detected",
    ]
    title: str
    severity: str
    status: str
    source: str
    cvss_score: float | None
    cve_id: str | None
    is_verified: bool
    asset_identifier: str | None = None
    asset_type: str | None = None
    service_host: str | None = None
    service_port: int | None = None
    service_protocol: str | None = None
    description: str | None = None
    recommendation: str | None = None


class SecurityScanComparisonResult(BaseModel):
    comparison_available: bool
    current_scan_id: UUID
    current_scan_created_at: datetime
    baseline_scan_id: UUID | None = None
    baseline_scan_created_at: datetime | None = None
    new_findings: list[
        SecurityComparisonFinding
    ] = Field(default_factory=list)
    persistent_findings: list[
        SecurityComparisonFinding
    ] = Field(default_factory=list)
    no_longer_detected: list[
        SecurityComparisonFinding
    ] = Field(default_factory=list)