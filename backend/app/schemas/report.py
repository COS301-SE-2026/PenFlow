from pydantic import BaseModel
from typing import List
from uuid import UUID
from datetime import datetime

#we can change this this is just for my rough draft

class SeverityEnum(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFORMATIONAL = "Informational"

class FindingSchema(BaseModel):
    id: UUID
    identifier: str 
    asset_type: str 
    findings: List[FindingSchema] = []

class AssetSchema(BaseModel):
    id: UUID
    identifier: str
    asset_type: str
    findings: List[FindingSchema] = []

class ScanReportResponse(BaseModel):
    scan_id: UUID
    domain: str
    status: str
    completed_at: datetime | None
    assets: List[AssetSchema]

    total_findings: int
    critical_count: int
    high_count: int