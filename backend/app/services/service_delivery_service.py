from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import AssessmentType, EngagementStatus
from app.models.engagement import Engagement
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.engagement_repository import EngagementRepository
from app.schemas.engagement import (
    EngagementAssetResponse,
    EngagementPagination,
    UserSummary,
)
from app.schemas.service_delivery import (
    ServiceDeliveryEngagementActionResponse,
    ServiceDeliveryEngagementDetail,
    ServiceDeliveryEngagementListItem,
    ServiceDeliveryEngagementListResponse,
    ServiceDeliveryFindingSummary,
    ServiceDeliveryRetestSummary,
    ServiceDeliveryScopingUpdate,
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


    @staticmethod
    def action_response(
        engagement: Engagement,
    ) -> ServiceDeliveryEngagementActionResponse:

        return ServiceDeliveryEngagementActionResponse(
            id=engagement.id,
            status=engagement.status,
            service_delivery_id=engagement.service_delivery_id,
            assigned_pentester_id=engagement.assigned_to,
            scheduled_start_date=engagement.scheduled_start_date,
            scheduled_end_date=engagement.scheduled_end_date,
            reviewed_at=engagement.reviewed_at,
            completed_at=engagement.completed_at,
            updated_at=engagement.updated_at,
        )


    @staticmethod
    async def require_owned_engagement(
        db: AsyncSession,
        engagement_id: UUID,
        service_delivery_id: UUID,
    ) -> Engagement:

        engagement = await ServiceDeliveryService.require_engagement(
            db,
            engagement_id=engagement_id,
        )

        if engagement.service_delivery_id != service_delivery_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This engagement is not assigned to you.",
            )

        return engagement


    @staticmethod
    async def claim_engagement(
        db: AsyncSession,
        engagement_id: UUID,
        service_delivery_id: UUID,
    ) -> ServiceDeliveryEngagementActionResponse:

        engagement = await ServiceDeliveryService.require_engagement(
            db,
            engagement_id=engagement_id,
        )

        if engagement.status != EngagementStatus.REQUESTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only requested engagements can be claimed.",
            )

        if engagement.service_delivery_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Engagement has already been claimed.",
            )

        claimed_engagement = await EngagementRepository.claim(
            db,
            engagement_id=engagement_id,
            service_delivery_id=service_delivery_id,
        )

        if claimed_engagement is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Engagement is no longer available to claim.",
            )

        response = ServiceDeliveryService.action_response(
            claimed_engagement,
        )

        await AuditRepository.create_log(
            db,
            user_id=service_delivery_id,
            action="engagement.claimed",
            entity_type="engagement",
            entity_id=claimed_engagement.id,
            metadata={
                "previous_status": EngagementStatus.REQUESTED.value,
                "new_status": EngagementStatus.SCOPING.value,
                "service_delivery_id": str(service_delivery_id),
            },
        )

        return response


    @staticmethod
    async def update_scoping(
        db: AsyncSession,
        engagement_id: UUID,
        service_delivery_id: UUID,
        request: ServiceDeliveryScopingUpdate,
    ) -> ServiceDeliveryEngagementActionResponse:

        engagement = await ServiceDeliveryService.require_owned_engagement(
            db,
            engagement_id=engagement_id,
            service_delivery_id=service_delivery_id,
        )

        if engagement.status != EngagementStatus.SCOPING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Scoping can only be updated while the engagement is in a scoping phase.",
            )

        changes: dict[str, object] = {}

        if "assessment_type" in request.model_fields_set:
            if request.assessment_type is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="assessment type cannot be null.",
                )
            changes["assessment_type"] = request.assessment_type

        if "scope" in request.model_fields_set:
            if request.scope is None:
                 raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="scope cannot be null.",
                )
            changes["scope"] = request.scope.strip()

        if "objective" in request.model_fields_set:
            changes["objective"] = (
                request.objective.strip()
                if request.objective is not None
                else None
            )

        if "constraints" in request.model_fields_set:
            changes["constraints"] = (
                request.constraints.strip()
                if request.constraints is not None
                else None
            )

        if "final_quote" in request.model_fields_set:
            changes["final_quote"] = request.final_quote

        if "estimated_duration_days" in request.model_fields_set:
            changes["estimated_duration_days"] = request.estimated_duration_days

        if not changes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No scoping fields were provided.",
            )

        old_values = {
            field: getattr(engagement, field)
            for field in changes
        }

        engagement = await EngagementRepository.update_fields(
            db,
            engagement=engagement,
            changes=changes,
        )

        response = ServiceDeliveryService.action_response(
            engagement,
        )

        await AuditRepository.create_log(
            db,
            user_id=service_delivery_id,
            action="engagement.scoping_updated",
            entity_type="engagement",
            entity_id=engagement.id,
            metadata={
                "changed_fields": list(changes.keys()),
                "old_values": {
                    key: (
                        value.value
                        if hasattr(value, "value")
                        else str(value)
                        if value is not None
                        else None
                    ) for key, value in old_values.items()
                },
                "new_values": {
                    key: (
                        value.value
                        if hasattr(value, "value")
                        else str(value)
                        if value is not None
                        else None
                    ) for key, value in changes.items()
                },
            },
        )

        return response