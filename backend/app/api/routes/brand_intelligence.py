import os
import uuid 
from fastapi import APIRouter, Depends, Header, HTTPException, status 
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

from app.repositories.user_repo import get_user_id_by_provider_id 

router = APIRouter(prefix="/brand-intelligence", tags=["Brand Intelligence"])
security_bearer = HTTPBearer()

CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]

INTERNAL_SECRET = os.getenv("INTERNAL_WEBHOOK_SECRET", "dev_secret_key_123")

@router.post("/trigger/{verified_domain_id}", response_model=BrandMonitoringResponse)
async def trigger_brand_scan(
    verified_domain_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    user_id = await get_user_id_by_provider_id(db, current_user["sub"])
    if not user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    service = BrandIntelligenceService(db)
    try:
        return await service.trigger_monitoring_run(
            verified_domain_id,
            user_id=str(user_id)
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except PermissionError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))

@router.get("/domain/{verified_domain_id}", response_model=BrandMonitoringResponse)
async def get_brand_candidates(
    verified_domain_id: uuid.UUID,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    user_id = await get_user_id_by_provider_id(db, current_user["sub"])
    if not user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    service = BrandIntelligenceService(db)
    try:
        monitor = await service.get_monitoring_overview(verified_domain_id, user_id=str(user_id))
        if not monitor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Brand monitoring not configured for this domain"
            )
        return monitor 
    except PermissionError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))


@router.patch("/candidate/{candidate_id}/status", response_model=BrandCandidateResponse)
async def update_candidate_status(
    candidate_id: uuid.UUID,
    current_user: CurrentUser,
    status_update: BrandCandidateUpdateStatus,
    db: AsyncSession = Depends(get_db),
):
    user_id = await get_user_id_by_provider_id(db, current_user["sub"])
    if not user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    service = BrandIntelligenceService(db)
    try:
        return await service.update_status(candidate_id, status_update.status, user_id=str(user_id))
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except PermissionError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))

@router.post("/internal/ingest", status_code=status.HTTP_200_OK)
async def ingest_monitoring_results(
    payload: BrandIngestionPayload,
    x_internal_token: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Internal webhook called by the Celery worker upon scan completion."""
    if x_internal_token != INTERNAL_SECRET:
        raise HTTPException(status_code=401, detail="Invalid internal token")

    service = BrandIntelligenceService(db)

    try:
        await service.ingest_worker_results(payload)
        return {"status": "success"}
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    return {"status": "success"}