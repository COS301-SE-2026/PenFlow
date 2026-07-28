import logging
from pathlib import Path
from typing import Annotated, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_user, get_current_user_optional
from app.api.middleware.rate_limiter import limiter
from app.models.base import ScanStatus
from app.repositories.report_repository import get_report_by_scan_id
from app.repositories.scan_repo import ScanRepository
from app.repositories.user_repo import get_user_id_by_provider_id
from app.schemas.report import EmailReportRequest
from app.schemas.scan import (
    AssetListResponse,
    DashboardAssetItem,
    DashboardFindingItem,
    FindingListResponse,
    InitiateScanRequest,
    InitiateScanResponse,
    MetricsResponse,
    RiskHistoryItem,
    ScanHistoryItem,
    ServiceListResponse,
)
from app.services.email_service import send_report_email
from app.services.scan_service import ScanService
from app.utils.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scans", tags=["Scans"])
# Use annoted for dependency injection
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]
CurrentUserOptional = Annotated[dict[str, Any] | None, Depends(get_current_user_optional)]


@router.get(
    "/",
    response_model=list[ScanHistoryItem],
    status_code=status.HTTP_200_OK,
)
async def list_scans(
    current_user: CurrentUser,
    db: DbSession,
    scan_status: ScanStatus | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    
    user_id = await get_user_id_by_provider_id(db, current_user["sub"])
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        return await ScanRepository.list_scans(db, user_id, scan_status, limit, offset)
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
@limiter.limit("3/10minutes")
async def initiate_ctem_scan(
    request: Request,
    payload: InitiateScanRequest,
    current_user: CurrentUserOptional,
    db: DbSession,
) -> InitiateScanResponse:
    try:
        user_id = None
        if current_user is not None:
            user_id = await get_user_id_by_provider_id(db, current_user["sub"])

        new_scan = await ScanService.start_scan(db, payload, user_id=user_id)

        return InitiateScanResponse(scan_id=new_scan.id, status=new_scan.status)

    except Exception:
        logger.exception("Failed to initiate scan for domain %s", payload.domain)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate scan",
        )


@router.get("/{scan_id}/status")
async def get_scan_status(
    scan_id: UUID,
    current_user: CurrentUserOptional,
    db: DbSession,
) -> dict[str, Any]:
    user_id = None
    if current_user is not None:
        user_id = await get_user_id_by_provider_id(db, current_user["sub"])

        if user_id is None:
            raise HTTPException(
                status_code = status.HTTP_404_NOT_FOUND,
                detail = "User not found",
            )
        
    status_info = await ScanRepository.get_scan_status(
        db,
        scan_id,
        user_id = user_id,
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
    db: DbSession,
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
    db: DbSession,
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


@router.get(
    "/{scan_id}/metrics",
    response_model=MetricsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_scan_metrics(
    scan_id: UUID,
    db: DbSession,
) -> dict[str, Any]:
    """
    Returns aggregated metrics for Risk Score, Findings,
    Assets, Services, Technologies.
    """
    metrics = await ScanRepository.get_scan_metrics(db, scan_id)
    if metrics is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    return metrics


@router.get(
    "/{scan_id}/findings",
    response_model=list[DashboardFindingItem],
    status_code=status.HTTP_200_OK,
)
async def get_scan_findings(
    scan_id: UUID,
    db: DbSession,
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    """
    Retrieves detailed findings for a scan, ordered by highest risk.
    """
    return await ScanRepository.get_findings_by_scan(
        db=db, scan_id=scan_id, severity=severity, limit=limit, offset=offset
    )


@router.get(
    "/{scan_id}/assets",
    response_model=list[DashboardAssetItem],
    status_code=status.HTTP_200_OK,
)
async def get_scan_assets(
    scan_id: UUID,
    db: DbSession,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    """
    Retrieves discovered assets along with their associated finding counts.
    """
    return await ScanRepository.get_assets_by_scan(
        db=db, scan_id=scan_id, limit=limit, offset=offset
    )


@router.get(
    "/{scan_id}/risk-history",
    response_model=list[RiskHistoryItem],
    status_code=status.HTTP_200_OK,
)
async def get_scan_risk_history(
    scan_id: UUID,
    db: DbSession,
) -> list[dict[str, Any]]:
    """
    Retrieves historical risk scores for the domain to render the risk over time graph.
    """
    return await ScanRepository.get_domain_risk_history(db=db, scan_id=scan_id)


@router.get(
    "/{scan_id}/findings-page",
    response_model=FindingListResponse,
    status_code=status.HTTP_200_OK,
)
async def get_scan_findings_page(
    scan_id: UUID,
    db: DbSession,
    severity: Optional[str] = Query(None, description="Filter by severity category"),
    search: Optional[str] = Query(None, description="Search query string"),
    sort_by: str = Query("severity", description="Sort criteria (severity, cvss, newest)"),
    limit: int = Query(12, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """
    Provides full card grid data for the Findings tab, including top metric counts
    and side drawer attributes.
    """
    items, counts = await ScanRepository.get_findings_page(
        db=db,
        scan_id=scan_id,
        severity=severity,
        search=search,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )
    return {
        "total": counts["total"],
        "counts": counts,
        "items": items,
    }


@router.get(
    "/{scan_id}/services-page",
    response_model=ServiceListResponse,
    status_code=status.HTTP_200_OK,
)
async def get_scan_services_page(
    scan_id: UUID,
    db: DbSession,
    protocol: Optional[str] = Query(None, description="Filter by protocol, TCP/UDP"),
    search: Optional[str] = Query(None, description="Search query string"),
    sort_by: str = Query("open", description="Sort criteria"),
    limit: int = Query(15, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """
    Provides full table data and summary cards for the Services tab.
    """
    items, counts = await ScanRepository.get_services_page(
        db=db,
        scan_id=scan_id,
        protocol=protocol,
        search=search,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )
    return {
        "total": counts["total"],
        "counts": counts,
        "items": items,
    }


@router.get(
    "/{scan_id}/assets-page",
    response_model=AssetListResponse,
    status_code=status.HTTP_200_OK,
)
async def get_scan_assets_page(
    scan_id: UUID,
    db: DbSession,
    asset_type: Optional[str] = Query(
        None, description="Filter by asset type (Domain, subdomain, ip)"
    ),
    severity: Optional[str] = Query(None, description="Filter by highest severity"),
    search: Optional[str] = Query(None, description="Search by query string"),
    sort_by: str = Query("risk", description="Sort criteria (risk, findings, identifier)"),
    limit: int = Query(15, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """
    Provides full table data and summary category cards for the assets tab.
    """
    items, counts = await ScanRepository.get_assets_page(
        db=db,
        scan_id=scan_id,
        asset_type=asset_type,
        severity=severity,
        search=search,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )
    return {"total": counts["total"], "counts": counts, "items": items}
