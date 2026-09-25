import uuid 
from fastapi import APIRouter, Depends, HTTPException, status 
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession 
from typing import Annotated, Any

from app.api.middleware.auth import get_current_user
from app.utils.db import get_db 
from app.services.brand_intelligence_service import BrandIntelligenceService 
from app.schemas.brand_intelligence import (
    BrandMonitoringResponse, 
    BrandCandidateResponse, 
    BrandCandidateUpdateStatus, 
    BrandIngestionPayload,
)

router = APIRouter(prefix="/brand-intelligence", tags=["Brand Intelligence"])
security_bearer = HTTPBearer()

CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]


@router.post("/trigger/{verified_domain_id}", response_model=BrandMonitoringResponse)
async def trigger_brand_scan(
    verified_domain_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: HTTPAuthorizationCredentials = Depends(security_bearer),
):
    service = BrandIntelligenceService(db)
    try:
        return await service.trigger_monitoring_run(
            verified_domain_id,
            token=auth.credentials)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))

@router.get("/domain/{verified_domain_id}", response_model=BrandMonitoringResponse)
async def get_brand_candidates(
    verified_domain_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = BrandIntelligenceService(db)
    monitor = await service.get_monitoring_overview(verified_domain_id)
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Brand monitoring not configured for this domain"
        )
    return monitor 

@router.patch("/candidate/{candidate_id}/status", response_model=BrandCandidateResponse)
async def update_candidate_status(
    candidate_id: uuid.UUID,
    status_update: BrandCandidateUpdateStatus,
    db: AsyncSession = Depends(get_db),
):
    service = BrandIntelligenceService(db)
    try:
        return await service.update_status(candidate_id, status_update.status)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))

@router.post("/internal/ingest", status_code=status.HTTP_200_OK)
async def ingest_monitoring_results(
    payload: BrandIngestionPayload,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Internal webhook called by the Celery worker upon scan completion."""
    service = BrandIntelligenceService(db)
    await service.ingest_worker_results(payload)
    return {"status": "success"}