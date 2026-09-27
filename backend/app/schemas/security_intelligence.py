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
    cve_id: str | None = None
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


class SecuritySeverityCounts(BaseModel):
    critical: int = Field(default=0, ge=0)
    high: int = Field(default=0, ge=0)
    medium: int = Field(default=0, ge=0)
    low: int = Field(default=0, ge=0)
    info: int = Field(default=0, ge=0)


class SecurityPortfolioFinding(BaseModel):
    finding_id: UUID
    scan_id: UUID
    domain: str
    title: str
    severity: str
    status: str
    source: str
    cvss_score: float | None
    cve_id: str | None
    is_verified: bool
    asset_identifier: str | None = None
    service_port: int | None = None


class SecurityPortfolioDomainRisk(BaseModel):
    rank: int = Field(ge=1)
    domain: str
    scan_id: UUID
    scan_type: str
    scan_created_at: datetime
    risk_score: int = Field(ge=0, le=100)
    active_finding_count: int = Field(ge=0)
    severity_counts: SecuritySeverityCounts
    top_findings: list[
        SecurityPortfolioFinding
    ] = Field(default_factory=list)


class SecurityRecurringIssue(BaseModel):
    identity_type: Literal[
        "cve",
        "title",
    ]
    identifier: str
    title: str
    cve_id: str | None
    sources: list[str] = Field(
        default_factory=list,
    )
    highest_severity: str
    affected_domain_count: int = Field(
        ge=2,
    )
    affected_domains: list[str] = Field(
        min_length=2,
    )
    occurrence_count: int = Field(ge=2)
    representative_findings: list[
        SecurityPortfolioFinding
    ] = Field(default_factory=list)


class SecurityPortfolioResult(BaseModel):
    portfolio_available: bool
    domain_count: int = Field(default=0, ge=0)
    active_finding_count: int = Field(
        default=0,
        ge=0,
    )
    severity_counts: SecuritySeverityCounts = Field(
        default_factory=SecuritySeverityCounts,
    )
    domains: list[
        SecurityPortfolioDomainRisk
    ] = Field(default_factory=list)
    recurring_issues: list[
        SecurityRecurringIssue
    ] = Field(default_factory=list)