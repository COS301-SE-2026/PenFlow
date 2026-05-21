#type: ignore
import logging

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.scan_repo import ScanRepository
from app.schemas.scan import ScanCallbackRequest
from app.utils.db import get_db
from app.services.report_service import queue_report_generation
from app.repositories.report_repository import mark_report_completed, mark_report_failed
from app.schemas.report import ReportCallbackRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["Internal Webhooks"])

@router.patch("/scans/{scan_id}/status", status_code=status.HTTP_200_OK)
async def update_scan_status_callback(
    scan_id: UUID,
    payload: ScanCallbackRequest,
    db: Session = Depends(get_db),
):
    try:
        queued_report = None

        scan = ScanRepository.get_scan_by_id(db, scan_id)

        if scan is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan not found",
            )

        scan.status = payload.status

        if payload.error_message:
            scan.error_message = payload.error_message

        if payload.results:
            ScanRepository.save_worker_results(
                db=db,
                scan_id=scan_id,
                results=payload.results,
            )

            queued_report = queue_report_generation(db, str(scan_id))
        else:
            db.commit()
            db.refresh(scan)

        return {
            "scan_id": str(scan.id),
            "status": scan.status.value,
            "report_status": queued_report["status"] if queued_report else None,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to process worker callback for %s", scan_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process callback",
        )

@router.patch("/reports/{scan_id}/status", status_code=status.HTTP_200_OK)
async def update_report_status_callback(
    scan_id: UUID,
    payload: ReportCallbackRequest,
    db: Session = Depends(get_db),
):
    try:
        if payload.status == "completed":
            if not payload.pdf_path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="pdf_path is required for completed reports",
                )

            report = mark_report_completed(
                db=db,
                scan_id=str(scan_id),
                pdf_path=payload.pdf_path,
            )

        elif payload.status == "failed":
            report = mark_report_failed(
                db=db,
                scan_id=str(scan_id),
                error_message=payload.error_message or "Report generation failed",
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid report status",
            )

        return {
            "scan_id": str(scan_id),
            "report_status": report.status.value if report else payload.status,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to process report callback for %s", scan_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process report callback",
        )