from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.base import ReportStatus


class SeverityEnum(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFORMATIONAL = "Informational"


class FindingSchema(BaseModel):
    id: UUID
    title: str
    severity: SeverityEnum
    model_config = ConfigDict(from_attributes=True)


class AssetSchema(BaseModel):
    id: UUID
    identifier: str
    asset_type: str
    findings: List[FindingSchema] = []
    model_config = ConfigDict(from_attributes=True)


class ScanReportResponse(BaseModel):
    scan_id: UUID
    domain: str
    status: str
    completed_at: datetime | None
    assets: List[AssetSchema]

    total_findings: int
    critical_count: int
    high_count: int


class ReportCallbackRequest(BaseModel):
    status: str
    pdf_path: str | None = None
    error_message: str | None = None


class EmailReportRequest(BaseModel):
    email: EmailStr

class ReportCreate(BaseModel):
    engagement_id: Optional[UUID] = None 
    scan_id: Optional[UUID] = None 
    version: int = Field(default=1, ge=1)

class ReportResponse(BaseModel):
    id: UUID
    scan_id: Optional[UUID] = None 
    engagement_id: Optional[UUID] = None 
    version: int 
    task_id: Optional[str] = None 
    status: ReportStatus 
    pdf_path: Optional[str] = None
    generated_at: Optional[datetime] = None 
    created_at: datetime 
    error_message: Optional[str] = None 

    class Config:
        from_attributes= True 

class ReportCallbackUpdate(BaseModel):
    status: ReportStatus 
    pdf_path: Optional[str] = None 
    error_message: Optional[str] = None 
