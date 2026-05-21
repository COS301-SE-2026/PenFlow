import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.scan_repo import ScanRepository
from app.schemas.scan import InitiateScanRequest, InitiateScanResponse, ScanHistoryItem
from app.services.scan_service import ScanService
from app.utils.db import get_db

logger = logging.getLogger(__name__)

router= APIRouter(prefix="/scans",tags=["Scans"])


@router.get(
    "/",
    response_model=list[ScanHistoryItem],
    status_code=status.HTTP_200_OK,
)
async def list_scans(db: AsyncSession = Depends(get_db)):
    try:
        return await ScanRepository.list_scans(db)
    except Exception:
        logger.exception("Failed to list scans")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve scan history",
        )

@router.post(
    "/",
    response_model=InitiateScanResponse,
    status_code=status.HTTP_202_ACCEPTED

)

async def initiate_ctem_scan(
    request: InitiateScanRequest,
    db: AsyncSession = Depends(get_db)
):
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
            detail="Failed to initiate scan"
        )

@router.get(
    "/{scan_id}/pdf",
    response_class=Response,
    status_code=status.HTTP_200_OK

)

async def download_scan_pdf(
    scan_id: str,

):

    """
    Generate and download a branded PDF report for a completed scan.
    Triggers WeasyPrint in the background/service layer.
    """

    #MOCK, I AM MOCKING THIS!!!!
    mock_pdf_content = b"%PDF-1.4\n%Mock PDF Document for PenFlow Phase 1\n"

    return Response(
        content=mock_pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="PenFlow_Report_{scan_id}.pdf"'
        }
    )