from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import NotificationType, RetestStatus
from app.repositories.audit_repository import AuditRepository
from app.repositories.engagement_repository import EngagementRepository
from app.repositories.retest_repository import RetestRepository
from app.schemas.retest import RetestFindingSummary, RetestListItem, RetestUpdate
from app.services.notification_service import NotificationService


class RetestService:
    @staticmethod
    async def update_retest(
        db: AsyncSession,
        retest_id: UUID,
        user_id: UUID,
        request: RetestUpdate,
    ) -> RetestListItem:
        retest = await RetestRepository.get_by_id(
            db,
            retest_id=retest_id,
        )

        if retest is None or retest.finding.engagement_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Retest was not found.",
            )

        previous_status = retest.status
        engagement_id = retest.finding.engagement_id

        engagement = await EngagementRepository.get_assigned_by_id(
            db,
            engagement_id=engagement_id,
            user_id=user_id,
        )

        if engagement is None:
            raise HTTPException(
                status_code = status.HTTP_404_NOT_FOUND,
                detail="Retest was not found."
            )

        if request.status in {RetestStatus.RESOLVED, RetestStatus.STILL_VULNERABLE}:
            retest.completed_at = datetime.now(timezone.utc)

        elif request.status in {RetestStatus.REQUESTED, RetestStatus.IN_PROGRESS}:
            retest.completed_at = None

        retest = await RetestRepository.update_retest(
            db,
            retest=retest,
            request=request,
        )

        await AuditRepository.create_log(
            db,
            user_id=user_id,
            action="retest.updated",
            entity_type="finding_retest",
            entity_id=retest.id,
            metadata={
                "engagement_id": str(retest.finding.engagement_id),
                "finding_id": str(retest.finding_id),
                "status": retest.status.value,
            },
        )

        await db.refresh(retest)

        completed_statuses = {
            RetestStatus.RESOLVED,
            RetestStatus.STILL_VULNERABLE,
        }

        if (
            previous_status not in completed_statuses
            and retest.status in completed_statuses
        ):
            notification_metadata = {
                "retest_id": str(retest.id),
                "finding_id": str(retest.finding_id),
                "status": retest.status.value,
            }

            await NotificationService.notify(
                db,
                recipient_id=engagement.requested_by,
                actor_id=user_id,
                notification_type=NotificationType.RETEST_COMPLETED,
                title="Re-test completed",
                message=f"A re-test for {engagement.title} has been completed.",
                engagement_id=engagement.id,
                metadata=notification_metadata,
            )

            await NotificationService.notify(
                db,
                recipient_id=engagement.service_delivery_id,
                actor_id=user_id,
                notification_type=NotificationType.RETEST_COMPLETED,
                title="Re-test completed",
                message=f"A re-test for {engagement.title} has been completed.",
                engagement_id=engagement.id,
                metadata=notification_metadata,
            )

        return RetestListItem(
            id=retest.id,
            finding=RetestFindingSummary(
                id=retest.finding.id,
                title=retest.finding.title,
                severity=retest.finding.severity,
            ),
            requested_by=retest.requested_by,
            assigned_to=retest.assigned_to,
            status=retest.status,
            notes=retest.notes,
            requested_at=retest.requested_at,
            completed_at=retest.completed_at,
        )