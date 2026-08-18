import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.base import EngagementStatus, EngagementType
from app.schemas.finding import FindingListItem


class SortOrder(str, enum.Enum):
    ASC = "asc"
    DESC = "desc"

class EngagementSortField(str, enum.Enum):
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    CLIENT = "client"
    STATUS = "status"
    REQUESTED_START_DATE = "requested_start_date"

class UserSummary(BaseModel):
    id: UUID
    full_name: str | None = None
    email: str | None = None
    role: str | None = None

class OrganisationSummary(BaseModel):
    id: UUID
    name: str

class EngagementAssetResponse(BaseModel):
    id: UUID
    identifier: str
    asset_type: str
    asset_metadata: dict[str, Any]
    verified_domain_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)

class EngagementCounts(BaseModel):
    all: int
    requested: int
    scoping: int
    in_progress: int
    review: int
    completed: int
    cancelled: int

class EngagementPagination(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool

class EngagementListItem(BaseModel):
    id: UUID
    title: str
    engagement_type: EngagementType
    priority: str
    status: EngagementStatus
    requested_start_date: date | None = None
    estimated_duration_days: int | None = None
    updated_at: datetime
    client_name: str
    asset_count: int
    target_date: date | None = None

class EngagementListResponse(BaseModel):
    items: list[EngagementListItem]
    counts: EngagementCounts
    pagination: EngagementPagination

class EngagementOverviewCounts(BaseModel):
    assets: int
    manual_findings: int
    automated_findings: int

class PreviousScanSummary(BaseModel):
    id: UUID
    domain: str
    completed_at: datetime | None = None
    relevant_findings: int
    reviewed_findings: int = 0

class EngagementDetailResponse(BaseModel):
    id: UUID
    title: str
    engagement_type: EngagementType
    priority: str
    status: EngagementStatus
    scope: str
    estimated_quote: Decimal
    estimated_duration_days: int | None = None
    requested_start_date: date | None = None
    target_date: date | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    client: UserSummary
    assigned_pentester: UserSummary | None = None
    assets: list[EngagementAssetResponse]
    counts: EngagementOverviewCounts
    recent_findings: list[FindingListItem]
    previous_scan: PreviousScanSummary | None = None

class EngagementMessageCreate(BaseModel):
    comment: str
    finding_id: UUID | None = None

class EngagementMessageResponse(BaseModel):
    id: UUID
    engagement_id: UUID
    finding_id: UUID | None = None
    user: UserSummary
    comment: str
    created_at: datetime

class EngagementMessageListResponse(BaseModel):
    items: list[EngagementMessageResponse]

class ActivityItemResponse(BaseModel):
    id: UUID
    action: str
    entity_type: str
    entity_id: UUID | None = None
    actor: UserSummary | None = None
    metadata: dict[str, Any]
    created_at: datetime

class ActivityListResponse(BaseModel):
    items: list[ActivityItemResponse]


class MessageClientSummary(BaseModel):
    id: UUID
    full_name: str | None
    email: str


class LatestMessageSummary(BaseModel):
    id: UUID
    comment: str
    sender_name: str | None
    sender_role: str
    created_at: datetime


class PentesterConversationSummary(BaseModel):
    engagement_id: UUID
    engagement_title: str
    client: MessageClientSummary
    last_message: LatestMessageSummary | None
    message_count: int
    unread_count: int


class PentesterConversationListResponse(BaseModel):
    items: list[PentesterConversationSummary]


class MarkMessagesReadResponse(BaseModel):
    marked_read: int


class EngagementStatusResponse(BaseModel):
    id: UUID
    status: EngagementStatus
    updated_at: datetime