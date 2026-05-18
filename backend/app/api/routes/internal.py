from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.scan import ScanCallbackRequest
#from app.repositories.scan_repo import ScanRepository
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["Internal Webhooks"])

@router.patch("/scans/{scan_id}/status", status_code=status.HTTP_200_OK)
async def update_scan_status_callback(
    scan_id: str,
    payload: ScanCallbackRequest,
    #db: Session = Depends(get_db)
):
    """
    Webhook for celery workers, report failures/ partial completions.
    """
    try:
        #is_partial = payload.status == ScanStatus.PARTIAL
        #ScanRepository.mark_scan_failed(
        #   db=db,
        #   scan_id=uuid.UUID(scan_id),
        #   error_message=payload.error_message,
        #   is_partial=is_partial
        #)

        logger.info(f"Worker reported status {payload.status} for scan {scan_id}")
        return {"message": f"Scan {scan_id} updated to {payload.status.value}"}

    except Exception as e:
        logger.error(f"Failed to process worker callback for {scan_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process callback"
            
        )