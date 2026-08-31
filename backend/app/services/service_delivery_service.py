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
            engagement_id=engagement_id,
        )

        if engagement is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Engagement could not be found.",
            )

        return engagement


    @staticmethod
    async def get_engagement(
        db: AsyncSession,
        engagement_id: UUID,
    ) -> ServiceDeliveryEngagementDetail:

        engagement = await ServiceDeliveryService.require_engagement(
            db,
            engagement_id=engagement_id,
        )

        assets = await EngagementRepository.get_assets(
            db,
            engagement_id=engagement_id,
        )

        client = await EngagementRepository.get_user_by_id(
            db,
            user_id=engagement.requested_by,
        )

        if client is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Engagement client could not be found.",
            )

        service_delivery = None

        if engagement.service_delivery_id is not None:
            service_delivery = await EngagementRepository.get_user_by_id(
                db,
                user_id=engagement.service_delivery_id,
            )

        assigned_pentester = None

        if engagement.assigned_to is not None:
            assigned_pentester = await EngagementRepository.get_user_by_id(
                db,
                user_id=engagement.assigned_to,
            )

        reviewer = None

        if engagement.reviewed_by is not None:
            reviewer = await EngagementRepository.get_user_by_id(
                db,
                user_id=engagement.reviewed_by,
            )

        (
            total_findings,
            critical_findings,
            high_findings,
            medium_findings,
            low_findings,
            findings_with_evidence,
        ) = await EngagementRepository.get_service_delivery_finding_summary(
            db,
            engagement_id=engagement_id,
        )

        (
            total_retests,
            requested_retests,
            in_progress_retests,
            resolved_retests,
            still_vulnerable_retests,
        ) = await EngagementRepository.get_service_delivery_retest_summary(
            db,
            engagement_id=engagement_id,
        )

        return ServiceDeliveryEngagementDetail(
            id=engagement.id,
            title=engagement.title,
            engagement_type=engagement.engagement_type,
            assessment_type=engagement.assessment_type,
            priority=engagement.priority,
            status=engagement.status,
            scope=engagement.scope,
            objective=engagement.objective,
            constraints=engagement.constraints,
            primary_contact=engagement.primary_contact,
            estimated_quote=engagement.estimated_quote,
            final_quote=engagement.final_quote,
            estimated_duration_days=engagement.estimated_duration_days,
            requested_start_date=engagement.requested_start_date,
            requested_end_date=engagement.requested_end_date,
            scheduled_start_date=engagement.scheduled_start_date,
            scheduled_end_date=engagement.scheduled_end_date,
            started_at=engagement.started_at,
            completed_at=engagement.completed_at,
            reviewed_by=(
                ServiceDeliveryService.user_summary(reviewer)
                if reviewer is not None
                else None
            ),
            reviewed_at=engagement.reviewed_at,
            review_note=engagement.review_note,
            client=ServiceDeliveryService.user_summary(client),
            service_delivery=(
                ServiceDeliveryService.user_summary(service_delivery)
                if service_delivery is not None
                else None
            ),
            assigned_pentester=(
                ServiceDeliveryService.user_summary(assigned_pentester)
                if assigned_pentester is not None
                else None
            ),
            assets=[
                EngagementAssetResponse.model_validate(asset)
                for asset in assets
            ],
            finding_summary=ServiceDeliveryFindingSummary(
                total=total_findings,
                critical=critical_findings,
                high=high_findings,
                medium=medium_findings,
                low=low_findings,
                with_evidence=findings_with_evidence,
            ),
            retest_summary=ServiceDeliveryRetestSummary(
                total=total_retests,
                requested=requested_retests,
                in_progress=in_progress_retests,
                resolved=resolved_retests,
                still_vulnerable=still_vulnerable_retests,
            ),
            created_at=engagement.created_at,
            updated_at=engagement.updated_at,
        )