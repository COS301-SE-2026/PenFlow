from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.base import ScanStatus


class InitiateScanRequest(BaseModel):
    domain: str = Field(...,description="The target domain to scan", json_schema_extra={"example": "exmpl.com"}) # noqa: E501
    email: EmailStr | None = Field(None,description="email to send the report to")

class InitiateScanResponse(BaseModel):
    scan_id: UUID
    status: ScanStatus

class ScanCallbackRequest(BaseModel):
    status: ScanStatus
    error_message: str | None = None

class ScanResponse(BaseModel):
    id: UUID
    domain: str
    status: ScanStatus
    progress: int
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None

    model_config = ConfigDict(from_attributes=True)