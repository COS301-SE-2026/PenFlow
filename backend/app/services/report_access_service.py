import logging
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import EngagementStatus, ReportStatus
from app.models.engagement import Engagement
from app.models.report import Report
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.engagement_repository import EngagementRepository
from app.repositories.pentester_profile_repository import (
    PentesterProfileRepository,
)
from app.repositories.report_repository import (
    get_by_engagement_and_version,
    get_latest_for_engagement,
)
from app.services.report_service import queue_engagement_report_generation
from app.services.scan_service import ScanService

logger = logging.getLogger(__name__)


class ReportAccessService:
    @staticmethod
    async def require_engagement(
        db: AsyncSession,
        engagement_id: UUID,
        user: User,
        *,
        manage: bool = False,
    ) -> Engagement:
        if manage and user.role != "service_delivery":
            raise HTTPException(
                status_code=403,
                detail="Service Delivery access required",
            )

        engagement = await EngagementRepository.get_by_id(
            db,
            engagement_id=engagement_id,
        )

        if engagement is None:
            raise HTTPException(404, "Report not found")

        if manage:
            allowed = engagement.service_delivery_id == user.id

        elif engagement.requested_by == user.id:
            allowed = engagement.status in {
                EngagementStatus.COMPLETED,
                EngagementStatus.RETESTING,
            }

        elif user.role == "service_delivery":
            allowed = True

        elif (
            user.role == "pentester"
            and engagement.assigned_to == user.id
        ):
            profile = await PentesterProfileRepository.get_by_user_id(
                db,
                user_id=user.id,
            )

            allowed = profile is not None and profile.is_active

        else:
            allowed = False

        if not allowed:
            raise HTTPException(404, "Report not found")

        return engagement

    @staticmethod
    async def require_download(
        db: AsyncSession,
        report: Report,
        user: User,
        *,
        service_delivery_only: bool = False,
    ) -> Report:

        if service_delivery_only and user.role != "service_delivery":
            raise HTTPException(
                status_code=403,
                detail="Service Delivery access required",
            )

        if (
            report.engagement_id is not None
            and report.scan_id is None
        ):
            await ReportAccessService.require_engagement(
                db,
                report.engagement_id,
                user,
                manage=False,
            )

        elif (
            report.scan_id is not None
            and report.engagement_id is None
        ):
            if service_delivery_only:
                raise HTTPException(404, "Report not found")

            await ScanService.require_scan_access(
                db,
                scan_id=report.scan_id,
                user_id=user.id,
            )

        else:
            raise HTTPException(404, "Report not found")

        if (
            report.status != ReportStatus.COMPLETED
            or not report.pdf_path
        ):
            raise HTTPException(404, "Report PDF not found")

        return report

    @staticmethod
    def metadata(report: Report) -> dict[str, Any]:
        return {
            "id": report.id,
            "report_id": report.id,
            "engagement_id": report.engagement_id,
            "scan_id": report.scan_id,
            "version": report.version,
            "status": report.status.value,
            "pdf_path": None,
            "generated_at": report.generated_at,
            "created_at": report.created_at,
            "error_message": (
                "Report generation failed. Contact Service Delivery."
                if report.status == ReportStatus.FAILED
                else None
            ),
        }

    @staticmethod
    async def retry(
        db: AsyncSession,
        engagement_id: UUID,
        user: User,
        version: int | None = None,
    ) -> dict[str, Any]:
        engagement = await ReportAccessService.require_engagement(
            db,
            engagement_id,
            user,
            manage=True,
        )

        if engagement.status != EngagementStatus.REVIEW:
            raise HTTPException(
                status_code=409,
                detail="Reports can only be retried during review",
            )

        latest = await get_latest_for_engagement(
            db,
            engagement_id,
        )

        if latest is None:
            raise HTTPException(404, "Report not found")

        if version is not None and version != latest.version:
            raise HTTPException(
                status_code=409,
                detail="Only the latest report can be retried",
            )

        result = await db.execute(
            update(Report).where(
                Report.id == latest.id,
                Report.status == ReportStatus.FAILED,
            ).values(
                status=ReportStatus.GENERATING,
                error_message=None,
            ).returning(Report.id)
        )

        if result.scalar_one_or_none() is None:
            await db.rollback()

            raise HTTPException(
                status_code=409,
                detail="Only a failed report can be retried",
            )

        try:
            await AuditRepository.create_log(
                db,
                user_id=user.id,
                action="report.retry_requested",
                entity_type="report",
                entity_id=latest.id,
                metadata={
                    "engagement_id": str(engagement_id),
                    "version": latest.version,
                },
                commit=False,
            )

            await db.commit()

        except Exception:
            await db.rollback()
            raise

        try:
            await queue_engagement_report_generation(
                db,
                engagement_id=engagement_id,
                version=latest.version,
            )

        except Exception as exc:
            await db.rollback()

            logger.exception(
                "Report retry failed for engagement %s",
                engagement_id,
            )

            raise HTTPException(
                status_code=503,
                detail="Report generation is temporarily unavailable",
            ) from exc

        report = await get_by_engagement_and_version(
            db,
            engagement_id,
            latest.version,
        )

        if report is None:
            raise HTTPException(404, "Report not found")

        return ReportAccessService.metadata(report)