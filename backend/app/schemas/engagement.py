import enum
import re
from datetime import date, datetime
from decimal import Decimal
from ipaddress import ip_address
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.base import EngagementStatus, EngagementType
from app.schemas.finding import FindingListItem

#regex for Label for hostname
#don't lead and end with -
# allows digit and character and charcter from 1-63
_LABEL = r"(?!-)[A-Za-z0-9-]{1,63}(?<!-)"


#regex:hostname must be labels separated by dots
_HOSTNAME_PATTERN = re.compile(rf"^{_LABEL}(\.{_LABEL})*$")


#regex:domain backend check
_DOMAIN_PATTERN = re.compile(rf"^{_LABEL}(\.{_LABEL})*\.[A-Za-z]{{2,}}$")
class SortOrder(str, enum.Enum):
    ASC = "asc"
    DESC = "desc"

class EngagementSortField(str, enum.Enum):
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    CLIENT = "client"
    STATUS = "status"
    REQUESTED_START_DATE = "requested_start_date"

#create request form use
class EngagementAssetRequestType(str, enum.Enum):
    DOMAIN = "domain"
    IP = "ip"
    HOSTNAME = "hostname"
    URL = "url"

# One asset row from the asset declaration section of the form.
class EngagementAssetCreate(BaseModel):
    type: EngagementAssetRequestType
    value: str = Field(..., min_length=1, max_length=2048)

    # Backend val matters cause this defines our legal pentest scope.
    @model_validator(mode="after")
    def validate_asset_value(self) -> Self:
        stripped_value = self.value.strip()

        if not stripped_value:
            raise ValueError("Asset value cannot be empty.")

        if self.type == EngagementAssetRequestType.IP:
            try:
                ip_address(stripped_value)
            except ValueError as error:
                raise ValueError("Asset value must be a valid IP address.") from error

        if self.type == EngagementAssetRequestType.URL and not (
            stripped_value.startswith("http://") or stripped_value.startswith("https://")
        ):
            raise ValueError("URL assets must start with http:// or https://.")

        #error message for domain and hostname
        if self.type == EngagementAssetRequestType.DOMAIN:
                    if len(stripped_value) > 253 or not _DOMAIN_PATTERN.match(stripped_value):
                        raise ValueError(
                            "Asset value must be a valid domain (e.g. example.com)."
                        )

        if self.type == EngagementAssetRequestType.HOSTNAME:
                    if len(stripped_value) > 253 or not _HOSTNAME_PATTERN.match(stripped_value):
                        raise ValueError(
                            "Asset value must be a valid hostname "
                            "(letters, digits, hyphens, and dots only)."
                )


        self.value = stripped_value
        return self

# Matching the Phase 3 engagement form.
# It creates a scoping ticket, WE DO NOT RUN SCAN HERE.
class EngagementCreateRequest(BaseModel):
    engagement_type: EngagementType
    objective: str = Field(..., min_length=1, max_length=5000)
    start_date: date | None = None
    end_date: date | None = None
    constraints: str | None = Field(default=None, max_length=5000)
    primary_contact: str | None = Field(default=None, max_length=255)
    assets: list[EngagementAssetCreate] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_date_range(self) -> Self:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date cannot be after end_date.")

        return self

class EngagementCreateResponse(BaseModel):
    id: UUID
    status: EngagementStatus
    engagement_type: EngagementType
    objective: str
    start_date: date | None = None
    end_date: date | None = None
    asset_count: int
    #quote gen fields
    estimated_quote: Decimal
    estimated_duration_days: int | None = None
    assigned_pentester_id: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EngagementRequestAssetResponse(BaseModel):
    id: UUID
    type: str
    value: str

# Small detail response for the intake endpoint.
# Dev has a bigger EngagementDetailResponse below for dashboard views.
class EngagementRequestDetailResponse(BaseModel):
    id: UUID
    status: EngagementStatus
    engagement_type: EngagementType
    objective: str
    start_date: date | None = None
    end_date: date | None = None
    constraints: str | None = None
    primary_contact: str | None = None
    assets: list[EngagementRequestAssetResponse]
    assigned_pentester_id: UUID | None = None
    created_at: datetime


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
