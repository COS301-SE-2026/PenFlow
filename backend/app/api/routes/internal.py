#type: ignore
import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.scan import ScanCallbackRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["Internal Webhooks"])

@router.patch("/scans/{scan_id}/status", status_code=status.HTTP_200_OK)
async def update_scan_status_callback(
    scan_id: str,
    payload: ScanCallbackRequest,
):
    """
    Webhook for celery workers, report failures/ partial completions.
    """
    try:

        logger.info("Worker reported status %s for scan %s", payload.status, scan_id)
        return {"message": f"Scan {scan_id} updated to {payload.status.value}"}

    except Exception:
        logger.exception("Failed to process worker callback for %s", scan_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process callback"

        )