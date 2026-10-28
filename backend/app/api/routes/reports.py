import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import require_service_delivery, require_user
from app.models.report import Report
from app.models.user import User
from app.repositories.report_repository import get_latest_for_engagement
from app.services.report_access_service import ReportAccessService
from app.services.report_storage_service import ReportStorageService
from app.utils.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Reports"])


async def authorised_download(
        db: AsyncSession,
        report_id: UUID,
        user: User,
        *,
        service_delivery_only: bool = False,
        request: Request | None = None,
) -> FileResponse | StreamingResponse:
    report = await db.get(Report, report_id)

    if request is not None:
        request.state.audit_phase3_report = (
            report is not None
            and report.engagement_id is not None
            and report.scan_id is None
        )

    if report is None:
        raise HTTPException(404, "Report PDF not found")

    await ReportAccessService.require_download(
        db,
        report,
        user,
        service_delivery_only=service_delivery_only,
    )

    storage_ref = report.pdf_path

    if storage_ref is None:
        raise HTTPException(404, "Report PDF not found")

    filename = (
        f"engagement_report_v{report.version}.pdf"
        if report.engagement_id is not None
        else f"PenFlow_Report_{report.scan_id}.pdf"
    )

    try:
        if ReportStorageService.is_s3():
            s3_object = ReportStorageService.get_s3_object(
                storage_ref,
            )

            return StreamingResponse(
                content=s3_object["Body"].iter_chunks(),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": (
                        f'attachment; filename="{filename}"'
                    ),
                    "Cache-Control": "no-store",
                    "X-Content-Type-Options": "nosniff",
                },
            )

        file_path = ReportStorageService.get_local_report_storage(
            storage_ref,
        )

        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type="application/pdf",
            headers={
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )

    except Exception as exc:
        logger.exception(
            "Failed to retrieve report %s",
            report_id,
        )

        raise HTTPException(
            status_code=503,
            detail="Report download is temporarily unavailable",
        ) from exc


@router.get(
    "/reports/{report_id}/download",
    summary="Download an authorised report",
    response_model=None,
)
async def download_report(
    report_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
) -> FileResponse | StreamingResponse:
    return await authorised_download(
        db,
        report_id,
        user,
        request=request,
    )


@router.get(
    "/service-delivery/engagements/{engagement_id}/report",
    summary="Download a report for Service Delivery oversight",
)
async def get_service_delivery_engagement_report(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> dict[str, Any]:
    await ReportAccessService.require_engagement(
        db,
        engagement_id,
        user,
        manage=False,
    )

    report = await get_latest_for_engagement(
        db,
        engagement_id,
    )

    if report is None:
        raise HTTPException(404, "Report not found")

    return ReportAccessService.metadata(report)


@router.get(
    "/service-delivery/reports/{report_id}/download",
    summary="Download a report for an assigned engagement",
    response_model=None,
)
async def service_delivery_download_report(
    report_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> FileResponse | StreamingResponse:
    return await authorised_download(
        db,
        report_id,
        user,
        service_delivery_only=True,
        request=request,
    )


@router.post(
    "/service-delivery/engagements/{engagement_id}/report/retry",
    summary="Retry a failed report for an assigned engagement",
)
async def service_delivery_retry_report(
    engagement_id: UUID,
    version: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> dict[str, Any]:
    return await ReportAccessService.retry(
        db,
        engagement_id,
        user,
        version,
    )