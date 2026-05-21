#I am just going to implement a rought draft so long until we get the worker logic figured out
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
    results: dict[str, Any] | None = None
    error_message: str | None = None