from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.base import RetestStatus, Severity


class RetestFindingSummary(BaseModel):
    id: UUID
    title: str
    severity: Severity

class RetestListItem(BaseModel):
    id: UUID
    finding: RetestFindingSummary
    requested_by: UUID | None = None
    assigned_to: UUID | None = None
    status: RetestStatus
    notes: str | None = None
    requested_at: datetime
    completed_at: datetime | None = None

class RetestUpdate(BaseModel):
    status: RetestStatus | None = None
    notes: str | None = None

class RetestListResponse(BaseModel):
    items: list[RetestListItem]

#findings the client allow to access
class RetestEligibleFinding(BaseModel):
    id: UUID
    title: str
    severity: Severity

class RetestEligibleFindingsResponse(BaseModel):
    items: list[RetestEligibleFinding]

#create many request at once
class RetestBulkCreate(BaseModel):
    finding_ids: list[UUID] = Field(..., min_length=1)

class RetestBulkCreateResponse(BaseModel):
    created: list[RetestListItem]
    engagement_status: str


