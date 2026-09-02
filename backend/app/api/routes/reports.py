from typing import Any 
from uuid import UUID 

from fastapi import APIRouter, Depends, HTTPException, status 
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select 
from sqlalchemy.ext.asyncio import AsyncSession 

from app.api.deps import get_db, get_current_user
from app.api.middleware.auth import get_current_user 
from app.models.report import Report, ReportStatus 
from app.repositories.engagement_repository import EngagementRepository 
from app.repositories.user_repo import get_user_id_by_provider_id 
from app.services.report_storage_service import ReportStorageService 
from app.tasks.report_tasks import render_engagement_report_pdf_task
from app.utils.db import get_db 

router = APIRouter(prefix="", tags=["Reports"])

async def resolve_user(db: AsyncSession, current_user: dict[str, Any]):
    user_id = await get_user_id_by_provider_id(db, current_user["sub"])
    if user_id: 
        user = await EngagementRepository.get_user_by_id(db, user_id) 
        if user: 
            return user 
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, 
        detail="User not present.",
    )

@router.get(
    "/reports/{report_id}/download",
    summary="Download engagement report"
)
async def download_report(
    report_id: UUID, 
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    user = await resolve_user(db, current_user) 

    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none() 

    if not report or not report.pdf_path: 
        raise HTTPException(status_code=404, detail="Report PDF not found") 

    if ReportStorageService.is_s3():
        try:
            s3_obj = ReportStorageService.get_s3_object(report.pdf_path) 
            return StreamingResponse(
                content=s3_obj["Body"],
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="engagement_report_v{report.version}.pdf"'}
            )
        except Exception as e: 
            raise HTTPException(status_code=500, detail=str(e))

    file_path = ReportStorageService.get_local_report_storage(report.pdf_path) 
    return FileResponse( 
        path=str(file_path), 
        filename=f"engagement_report_v{report.version}.pdf",
        media_type="application/pdf"
    )

@router.get(
    "/service-delivery/engagements/{engagement_id}/report", 
    summary="Get report status and metadata for service delivery review"
)
async def get_service_delivery_engagement_report(
    engagement_id: UUID, 
    db: AsyncSession = Depends(get_db), 
    current_user: dict[str, Any] = Depends(get_current_user),
):
    user = await resolve_user(db, current_user) 

    result = await db.execute(
        select(Report)
        .where(Report.engagement_id == engagement_id)
        .order_by(Report.version.desc())
    )
    report = result.scalars().first()

    if not report: 
        raise HTTPException(status_code=404, detail="Report not found for this engagement")

    return {
        "repord_id": report.id, 
        "engagement_id": report.engagement_id, 
        "version": report.version, 
        "status": report.status.value if hasattr(report.status, "value") else report.status,
        "pdf_path": report.pdf_path,
    }

@router.get(
    "/service-delivery/reports/{report_id}/download",
    summary="Service delivery download report endpoint"
)
async def service_delivery_download_report(
    report_id: UUID, 
    db: AsyncSession = Depends(get_db), 
    current_user: dict[str, Any] = Depends(get_current_user),
): 
    return await download_report(report_id=report_id, db=db, current_user=current_user)

