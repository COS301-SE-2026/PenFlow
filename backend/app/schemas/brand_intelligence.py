import uuid 
from datetime import datetime 
from typing import Any
from pydantic import BaseModel, Field 

from app.models.brand_intelligence import BrandRiskLevel, BrandCandidateStatus 

class BrandCandidateBase(BaseModel):
    candidate_domain: str 
    normalized_domain: str 
    risk_score: int = Field(ge=0, le=100)
    risk_level: BrandRiskLevel 
    status: BrandCandidateStatus = BrandCandidateStatus.NEW 
    evidence: dict[str, Any] = {}

class BrandCandidateIngestItem(BaseModel):
    candidate_domain: str 
    normalized_domain: str 
    risk_score: int 
    risk_level: BrandRiskLevel 
    evidence: dict[str, Any]

class BrandIngestionPayload(BaseModel):
    brand_monitoring_id: uuid.UUID 
    candidates: list[BrandCandidateIngestItem]

class BrandCandidateUpdateStatus(BaseModel):
    status: BrandCandidateStatus 

class BrandCandidateResponse(BrandCandidateBase):
    id: uuid.UUID 
    brand_monitoring_id: uuid.UUID 
    first_seen: datetime 
    last_seen: datetime 
    resolved_at: datetime | None = None 

    class Config:
        from_attributes = True 

class BrandMonitoringResponse(BaseModel):
    id: uuid.UUID 
    verified_domain_id: uuid.UUID 
    is_active: bool 
    last_run_at: datetime | None = None 
    next_run_at: datetime | None = None 
    created_at: datetime 
    candidates: list[BrandCandidateResponse] = []

    class Config:
        from_attributes = True 