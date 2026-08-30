from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator

from typing import Self

from app.models.base import \
(
    AssessmentType,
    EngagementStatus,
    EngagementType,
    FindingStatus,
    Severity,
)
from app.schemas.engagement import EngagementAssetResponse, EngagementPagination, UserSummary

class ServiceDeliveryScopingUpdate(BaseModel):
    assessment_type: AssessmentType | None = None
    scope: str | None = Field(default=None, min_length=1, max_length=10000)
    objective: str | None = Field(default=None, max_length=5000)
    constraints: str | None = Field(default=None, max_length=5000)
    final_quote: Decimal | None = Field(default=None, ge=0)
    estimated_duration_days: int | None = Field(default=None, ge=1)

class ServiceDeliveryPentesterAssignment(BaseModel):
    pentester_id: UUID

class ServiceDeliveryScheduleRequest(BaseModel):
    scheduled_start_date: date
    scheduled_end_date: date

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.scheduled_start_date > self.scheduled_end_date:
            raise ValueError(
                "scheduled_start_date cannot be after scheduled_end_date."
            )

        return self

class ServiceDeliveryReassignRequest(BaseModel):
    pentester_id: UUID
    reason: str = Field(..., min_length=1, max_length=2000)

class ServiceDeliveryRescheduleRequest(BaseModel):
    scheduled_start_date: date
    scheduled_end_date: date
    reason: str = Field(..., min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.scheduled_start_date > self.scheduled_end_date:
            raise ValueError(
                "scheduled_start_date cannot be after scheduled_end_date."
            )

        return self

class ServiceDeliveryReviewReturnRequest(BaseModel):
    review_note: str = Field(..., min_length=1, max_length=5000)

class ServiceDeliveryCancelRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)

class ServiceDeliveryEngagementListItem(BaseModel):
    id: UUID
    title: str

    client: UserSummary

    engagement_type: EngagementType
    assessment_type: AssessmentType

    priority: str
    status: EngagementStatus

    service_delivery: UserSummary | None = None
    assigned_pentester: UserSummary | None = None

    requested_start_date: date | None = None
    requested_end_date: date | None = None

    scheduled_start_date: date | None = None
    scheduled_end_date: date | None = None

    final_quote: Decimal | None = None

    created_at: datetime
    updated_at: datetime

class ServiceDeliveryEngagementListResponse(BaseModel):
    items: list[ServiceDeliveryEngagementListItem]
    pagination: EngagementPagination

class ServiceDeliveryFindingSummary(BaseModel):
    total: int
    critical: int
    high: int
    medium: int
    low: int
    with_evidence: int

class ServiceDeliveryRetestSummary(BaseModel):
    total: int
    requested: int
    in_progress: int
    resolved: int
    still_vulnerable: int

class ServiceDeliveryReportSummary(BaseModel):
    id: UUID
    status: str
    generated_at: datetime | None = None

class ServiceDeliveryEngagementDetail(BaseModel):
    id: UUID
    title: str

    engagement_type: EngagementType
    assessment_type: AssessmentType
    priority: str
    status: EngagementStatus

    scope: str
    objective: str | None = None
    constraints: str | None = None
    primary_contact: str | None = None

    estimated_quote: Decimal
    final_quote: Decimal | None = None
    estimated_duration_days: int | None = None

    requested_start_date: date | None = None
    requested_end_date: date | None = None

    scheduled_start_date: date | None = None
    scheduled_end_date: date | None = None

    started_at: datetime | None = None
    completed_at: datetime | None = None

    reviewed_by: UserSummary | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None

    client: UserSummary
    service_delivery: UserSummary | None = None
    assigned_pentester: UserSummary | None = None

    assets: list[EngagementAssetResponse]

    finding_summary: ServiceDeliveryFindingSummary
    retest_summary: ServiceDeliveryRetestSummary

    created_at: datetime
    updated_at: datetime

class ServiceDeliveryEngagementActionResponse(BaseModel):
    id: UUID
    status: EngagementStatus
    service_delivery_id: UUID | None = None
    assigned_pentester_id: UUID | None = None
    scheduled_start_date: date | None = None
    scheduled_end_date: date | None = None
    reviewed_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime


class ServiceDeliveryDashboardCounts(BaseModel):
    requested: int
    scoping: int
    scheduled: int
    in_progress: int
    review: int
    completed: int
    cancelled: int
    needs_attention: int


class ServiceDeliveryDashboardEngagement(BaseModel):
    id: UUID
    title: str
    status: EngagementStatus
    assessment_type: AssessmentType
    priority: str

    client: UserSummary
    service_delivery: UserSummary | None = None
    assigned_pentester: UserSummary | None = None

    scheduled_start_date: date | None = None
    scheduled_end_date: date | None = None

    updated_at: datetime


class ServiceDeliveryDashboardResponse(BaseModel):
    counts: ServiceDeliveryDashboardCounts

    unclaimed_requests: list[ServiceDeliveryDashboardEngagement]
    awaiting_review: list[ServiceDeliveryDashboardEngagement]
    upcoming_engagements: list[ServiceDeliveryDashboardEngagement]


class ServiceDeliveryPentesterCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    specialisations: list[AssessmentType] = Field(..., min_length=1)


class ServiceDeliveryPentesterListItem(BaseModel):
    id: UUID
    full_name: str
    email: str

    is_active: bool
    availability_status: str
    specialisations: list[AssessmentType]

    assigned_engagements: int
    created_at: datetime


class ServiceDeliveryPentesterListResponse(BaseModel):
    items: list[ServiceDeliveryPentesterListItem]
    pagination: EngagementPagination


class ServiceDeliveryPentesterDetail(BaseModel):
    id: UUID
    full_name: str
    email: str

    is_active: bool
    availability_status: str
    specialisations: list[AssessmentType]

    assigned_engagements: int
    scheduled_engagements: int
    in_progress_engagements: int

    created_at: datetime


class ServiceDeliveryFindingListItem(BaseModel):
    id: UUID
    title: str
    severity: Severity
    status: FindingStatus

    engagement_asset_id: UUID | None = None
    asset_identifier: str | None = None

    source: str
    is_verified: bool

    cvss_score: Decimal | None = None
    cve_id: str | None = None

    created_at: datetime


class ServiceDeliveryFindingListResponse(BaseModel):
    items: list[ServiceDeliveryFindingListItem]
    pagination: EngagementPagination


class ServiceDeliveryFindingDetail(BaseModel):
    id: UUID
    engagement_id: UUID
    engagement_asset_id: UUID | None = None
    asset_identifier: str | None = None

    source: str
    title: str
    description: str | None = None
    recommendation: str | None = None

    severity: Severity
    status: FindingStatus
    is_verified: bool

    cvss_score: Decimal | None = None
    cve_id: str | None = None

    created_by: UUID | None = None
    created_at: datetime