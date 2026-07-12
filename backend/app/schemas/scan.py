#I am just going to implement a rought draft so long until we get the worker logic figured out
from datetime import datetime
from typing import Any
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

class ScanHistoryItem(BaseModel):
    id: UUID
    domain: str
    created_at: datetime
    status: ScanStatus
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