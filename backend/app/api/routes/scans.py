
import logging
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status 
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.report_repository import get_report_by_scan_id
from app.repositories.scan_repo import ScanRepository
from app.schemas.report import EmailReportRequest
from app.schemas.scan import InitiateScanRequest, InitiateScanResponse, ScanHistoryItem
from app.services.email_service import send_report_email
from app.services.scan_service import ScanService
from app.utils.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scans", tags=["Scans"])


@router.get(
    "/",
    response_model=list[ScanHistoryItem],
    status_code=status.HTTP_200_OK,
)
async def list_scans(
    scan_status: Optional[str] = Query(None, alias="status", description="Filter by scan status"),
    limit: int = Query(50, description="Limit results returned", le=100),
    db: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    try:
        return await ScanRepository.list_scans(db, status=scan_status, limit=limit)
    except Exception:
        logger.exception("Failed to list scans")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve scan history",
        )

@router.post(
    "/",
    response_model=InitiateScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
)

async def initiate_ctem_scan(
    request: InitiateScanRequest,
    db: AsyncSession = Depends(get_db)
) -> InitiateScanResponse:
    try:
        new_scan = await ScanService.start_scan(db, request)

        return InitiateScanResponse(
            scan_id=new_scan.id,
            status=new_scan.status
        )

    except Exception:
        logger.exception("Failed to initiate scan for domain %s", request.domain)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate scan",
        )


@router.get("/{scan_id}/status")
async def get_scan_status(
    scan_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    status_info = await ScanRepository.get_scan_status(
        db,
        scan_id,
    )

    if not status_info:
        raise HTTPException(
            status_code=404,
            detail="Scan not found",
        )
    
    return status_info


@router.get(
    "/{scan_id}/pdf",
    response_class=FileResponse,
    status_code=status.HTTP_200_OK,
)
async def download_scan_pdf(
    scan_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:

    report = await get_report_by_scan_id(db, str(scan_id))

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    if report.status.value != "completed" or not report.pdf_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report is not ready yet",
        )

    pdf_path = Path(report.pdf_path)

    if not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF file not found on server",
        )

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"PenFlow_Report_{scan_id}.pdf",
    )



@router.post(
    "/{scan_id}/email-report",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Report is not ready yet"},
        404: {"description": "Scan not found"},
    },
)
async def email_scan_report(
    scan_id: UUID,
    request: EmailReportRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    scan = await ScanRepository.get_scan_by_id(db, scan_id)

    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    report = await get_report_by_scan_id(db, str(scan_id))

    if not report or report.status.value != "completed" or not report.pdf_path:
        raise HTTPException(status_code=400, detail="Report is not ready yet")

    send_report_email(
        to_email=request.email,
        domain=str(scan.domain),
        pdf_path=str(report.pdf_path),
    )

    return {"message": "Report emailed successfully"}

@router.post(
    "/{scan_id}/active",
    status_code=status.HTTP_202_ACCEPTED,
)
async def initiate_active_scan(
    scan_id: UUID,
    db: AsyncSession = Depends(get_db)
) ->  dict[str, str]
    """
    Initaite our Phase 2.
    Designed to be called after the use of Phase 1 assets/
    """
    scan = await ScanRepository.get_scan_by_id(db, scan_id)

    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            details="Scan not found",
        )

    if scan.status.value not in ["completed", "partial"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phase 1 before initiating Phase 2."
        )

    # Triggering the phase 2 Celery workers
    celery_app.send_task("scan.phase2_full", args=[str(scan_id), scan.domain])

    await ScanRepository.update_scan_status(db, scan_id, "running")

    return {
        "message": "Phase 2 active scan initiated"
        "scan_id": str(scan_id)
    }