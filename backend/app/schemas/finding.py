from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import FindingReviewStatus, FindingStatus, Severity


class EvidenceFileResponse(BaseModel):
    id: UUID
    file_name: str
    mime_type: str | None = None
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)

class FindingCreate(BaseModel):
    engagement_asset_id: UUID | None = None
    title: str = Field(..., min_length=1, max_length=255)
    severity: Severity
    cvss_score: Decimal | None = Field(default=None, ge=0, le=10)
    cve_id: str | None = Field(default=None, max_length=50)
    description: str | None = None
    recommendation: str | None = None

class FindingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    engagement_asset_id: UUID | None = None
    severity: Severity | None = None
    cvss_score: Decimal | None = Field(default=None, ge=0, le=10)
    cve_id: str | None = Field(default=None, max_length=50)
    description: str | None = None
    recommendation: str | None = None
    status: FindingStatus | None = None
    review_status: FindingReviewStatus | None = None

class FindingListItem(BaseModel):
    id: UUID
    engagement_id: UUID | None = None
    engagement_asset_id: UUID | None = None
    source: str
    status: FindingStatus
    review_status: FindingReviewStatus | None = None
    severity: Severity
    cvss_score: Decimal | None = None
    cve_id: str | None = None
    title: str
    description: str | None = None
    created_at: datetime
    asset_identifier: str | None = None

    model_config = ConfigDict(from_attributes=True)

class FindingDetail(FindingListItem):
    recommendation: str | None = None
    created_by: UUID | None = None
    evidence_files: list[EvidenceFileResponse] = []

class FindingPagination(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool

class FindingListResponse(BaseModel):
    items: list[FindingListItem]
    pagination: FindingPagination