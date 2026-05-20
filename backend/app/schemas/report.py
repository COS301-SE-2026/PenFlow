from datetime import datetime
from enum import Enum
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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
    model_config = ConfigDict(from_attributes=True)