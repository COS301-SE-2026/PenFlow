import uuid 
from fastapi import APIRouter, Depends, HTTPException, status 
from sqlalchemy.orm import Session 

from app.db.session import get_db 
from app.services.brand_intelligence_service import BrandIntelligenceService 
from app.schemas.brand_intelligence import (
    BrandMonitoringResponse,
    BrandCandidateResponse,
    BrandCandidateUpdateStatus,
    BrandIngestionPayload,
)

router = APIRouter(prefix="/brand-intelligence", tags=["Brand Intelligence"])


@router.post("/trigger/{verified_domain_id}", response_model=BrandMonitoringResponse)
def trigger_brand_scan(
    verified_domain_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    service = BrandIntelligenceService(db)
    try:
        return service.trigger_monitoring_run(verified_domain_id)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))

@router.get("/domain/{verified_domain_id}", response_model=BrandMonitoringResponse)
def get_brand_candidates(
    verified_domain_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    service = BrandIntelligenceService(db)
    monitor = service.get_monitoring_overview(verified_domain_id)
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Brand monitoring not congigured for this domain"
        )
    return monitor 

@router.patch("/candidate/{candidate_id}/status", response_model=BrandCandidateResponse)
def update_candidate_status(
    candidate_id: uuid.UUID,
    status_update: BrandCandidateUpdateStatus,
    db: Session = Depends(get_db),
):
    service = BrandIntelligenceService(db)
    try:
        return service.update_status(candidate_id, status_update.status)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))

@router.post("/integrate/ingest", status_code=status.HTTP_200_OK)
def ingest_monitoring_results(
    payload: BrandIngestionPayload,
    db: Session = Depends(get_db),
):
    """
    Internal webhook called by the Celery worker upon scan completion.
    """
    service = BrandIntelligenceService(db)
    service.ingest_worker_results(payload)
    return {"status": "success"}