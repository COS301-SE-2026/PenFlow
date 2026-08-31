from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import AssessmentType, EngagementStatus
from app.models.engagement import Engagement
from app.models.user import User
from app.repositories.engagement_repository import EngagementRepository
from app.schemas.engagement import (
    EngagementAssetResponse,
    EngagementPagination,
    UserSummary,
)
from app.schemas.service_delivery import (
    ServiceDeliveryEngagementDetail,
    ServiceDeliveryEngagementListItem,
    ServiceDeliveryEngagementListResponse,
    ServiceDeliveryFindingSummary,
    ServiceDeliveryRetestSummary,
)


class ServiceDeliveryService:

    @staticmethod
    def user_summary(user: User) -> UserSummary:
        return UserSummary(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            role=user.role,
        )


    @staticmethod
    async def list_engagements(
        db: AsyncSession,
        *,
        engagement_status: EngagementStatus | None,
        assessment_type: AssessmentType | None,
        search: str | None,
        pentester_id: UUID | None,
        assigned: bool | None,
        limit: int,
        offset: int,
    ) -> ServiceDeliveryEngagementListResponse:

        rows, total = (
            await EngagementRepository.list_for_service_delivery(
                db,
                engagement_status=engagement_status,
                assessment_type=assessment_type,
                search=search,
                pentester_id=pentester_id,
                assigned=assigned,
                limit=limit,
                offset=offset,
            )
        )

        items = [
            ServiceDeliveryEngagementListItem(
                id=engagement.id,
                title=engagement.title,
                client=ServiceDeliveryService.user_summary(client),
                engagement_type=engagement.engagement_type,
                assessment_type=engagement.assessment_type,
                priority=engagement.priority,
                status=engagement.status,
                service_delivery=(
                    ServiceDeliveryService.user_summary(service_delivery)
                    if service_delivery is not None
                    else None
                ),
                assigned_pentester=(
                    ServiceDeliveryService.user_summary(pentester)
                    if pentester is not None
                    else None
                ),
                requested_start_date=engagement.requested_start_date,
                requested_end_date=engagement.requested_end_date,
                scheduled_start_date=engagement.scheduled_start_date,
                scheduled_end_date=engagement.scheduled_end_date,
                final_quote=engagement.final_quote,
                created_at=engagement.created_at,
                updated_at=engagement.updated_at,
            ) for (
                engagement,
                client,
                service_delivery,
                pentester,
            ) in rows
        ]

        return ServiceDeliveryEngagementListResponse(
            items=items,
            pagination=EngagementPagination(
                total=total,
                limit=limit,
                offset=offset,
                has_more=offset + len(items) < total,
            ),
        )


    @staticmethod
    async def require_engagement(
        db: AsyncSession,
        engagement_id: UUID,
    ) -> Engagement:
        engagement = await EngagementRepository.get_by_id(
            db,
            engagement_id=engagement,
        )

        if engagement is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Engagement could not be found.",
            )

        return engagement


    @staticmethod
    async def get_engagement(
        
    )