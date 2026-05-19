#type: ignore

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Response, status

from app.models.base import ScanStatus
from app.schemas.scan import InitiateScanRequest, InitiateScanResponse

router= APIRouter(prefix="/scans",tags=["Scans"])

@router.post(
    "/",
    response_model=InitiateScanResponse,
    status_code=status.HTTP_202_ACCEPTED

)

async def initiate_ctem_scan(
    request: InitiateScanRequest,
    #db stuff 

):

#Phase 1 this is the no auth scan also just a rough implementation for now until we have the other
#logic figured out

    try:
    #I'm going to pass the validated request to the service layer
    #db stuff
    #placeholder return

        return InitiateScanResponse(
            scan_id=uuid.uuid4(),
            status=ScanStatus.QUEUED

        )
    except Exception:
    #Once proper logic is setup I'll rather log this and return a 500/specific 400 code 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate scan"
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
    #db: Session = Depends(get db)

):

    """
    Generate and download a branded PDF report for a completed scan.
    Triggers WeasyPrint in the background/service layer.
    """

    #pdf_bytes = await ReportService.generate_pdf(db=db, scan_id=scan_id)
    #if not pdf_bytes:
    #   raise HTTPException(status_code=404, detail="Report not found or not completed.")

    #MOCK, I AM MOCKING THIS!!!!
    mock_pdf_content = b"%PDF-1.4\n%Mock PDF Document for PenFlow Phase 1\n"

    return Response(
        content=mock_pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="PenFlow_Report_{scan_id}.pdf"'
        }
    )