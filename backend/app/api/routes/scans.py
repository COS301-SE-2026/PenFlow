#type: ignore

import uuid
from datetime import datetime, timezone
from app.repositories.scan_repo import ScanRepository
from fastapi import APIRouter, Depends, HTTPException, Response, status
from uuid import UUID
from app.schemas.scan import InitiateScanRequest, InitiateScanResponse
from sqlalchemy.orm import Session
from app.services.scan_service import ScanService
from app.utils.db import get_db
from app.repositories.report_repository import get_report_by_scan_id
from app.schemas.report import EmailReportRequest
from app.services.email_service import send_report_email

router= APIRouter(prefix="/scans",tags=["Scans"])

@router.post(
    "/",
    response_model=InitiateScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
)

async def initiate_ctem_scan(
    request: InitiateScanRequest,
    db: Session = Depends(get_db),
):
    try:
        scan = await ScanService.start_scan(db, request)

        return InitiateScanResponse(
            scan_id=scan.id,
            status=scan.status,
        )

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate scan",
        )

@router.get(
    "/{scan_id}/report",
    status_code=status.HTTP_200_OK
)
async def get_scan_report(scan_id: str):
    """
    Retrieve full OSINT report for a specific scan.
    Mock from frontend
    """
    return{
        "scan_id": scan_id,
        "domain": "jeandre.co",
        "status": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "assets": [
            {
                "id": str(uuid.uuid4()),
                "identifier": "jeandre.co",
                "asset_type": "Domain",
                "findings": [
                    {
                        "id": str(uuid.uuid4()),
                        "title": "Missing DMARC",
                        "severity": "Medium"
                    }
                ]
            }
        ],
        "total_findings": 1,
        "critical_count": 0,
        "high_count": 0
    }


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


