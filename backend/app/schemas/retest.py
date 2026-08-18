from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

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