import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.schemas.scan import ScanCallbackRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["Internal Webhooks"])

@router.patch("/scans/{scan_id}/status", status_code=status.HTTP_200_OK)
async def update_scan_status_callback(
    scan_id: str,
    payload: ScanCallbackRequest,
)-> Any:
    """
    Webhook for celery workers, report failures/ partial completions.
    """
    safe_scan_id = scan_id.replace('\n', '').replace('\r', '')

    try:
        safe_status = str(payload.status.value).replace('\n', '').replace('\r', '')

        logger.info("Worker reported status %s for scan %s", safe_status, safe_scan_id)
        return {"message": f"Scan {safe_scan_id} updated to {safe_status}"}

    except Exception:
        logger.exception("Failed to process worker callback for %s", safe_scan_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process callback"

        )