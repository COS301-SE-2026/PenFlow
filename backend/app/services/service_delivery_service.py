import logging
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import (
    AssessmentType,
    EngagementStatus,
    FindingStatus,
    NotificationType,
    ReportStatus,
    Severity,
)
from app.models.engagement import Engagement
from app.models.evidence_file import EvidenceFile
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.engagement_repository import EngagementRepository
from app.repositories.finding_repository import FindingRepository
from app.repositories.pentester_profile_repository import PentesterProfileRepository
from app.repositories.report_repository import get_latest_for_engagement
from app.repositories.retest_repository import RetestRepository
from app.repositories.user_repo import UserRepository
from app.schemas.engagement import (
    ActivityItemResponse,
    ActivityListResponse,
    EngagementAssetResponse,
    EngagementPagination,
    LatestMessageSummary,
    MessageClientSummary,
    ServiceDeliveryConversationListResponse,
    ServiceDeliveryConversationSummary,
    UserSummary,
)
from app.schemas.retest import (
    RetestFindingSummary,
    RetestListItem,
    RetestListResponse,
)
from app.schemas.service_delivery import (
    ServiceDeliveryCancelRequest,
    ServiceDeliveryDashboardCounts,
    ServiceDeliveryDashboardEngagement,
    ServiceDeliveryDashboardResponse,
    ServiceDeliveryEngagementActionResponse,
    ServiceDeliveryEngagementDetail,
    ServiceDeliveryEngagementListItem,
    ServiceDeliveryEngagementListResponse,
    ServiceDeliveryFindingDetail,
    ServiceDeliveryFindingListItem,
    ServiceDeliveryFindingListResponse,
    ServiceDeliveryFindingSummary,
    ServiceDeliveryPentesterAssignment,
    ServiceDeliveryPentesterCreate,
    ServiceDeliveryPentesterDetail,
    ServiceDeliveryPentesterListItem,
    ServiceDeliveryPentesterListResponse,
    ServiceDeliveryReassignRequest,
    ServiceDeliveryRescheduleRequest,
    ServiceDeliveryRetestSummary,
    ServiceDeliveryReviewReturnRequest,
    ServiceDeliveryScheduleRequest,
    ServiceDeliveryScopingUpdate,
)
from app.services.keycloak_admin_service import KeycloakAdminError, KeycloakAdminService
from app.services.notification_service import NotificationService
from app.tasks.email_tasks import send_engagement_report_email_task

logger = logging.getLogger(__name__)

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

        await NotificationService.notify(
            db,
            recipient_id=claimed_engagement.requested_by,
            actor_id=service_delivery_id,
            notification_type=NotificationType.ENGAGEMENT_CLAIMED,
            title="Engagement request accepted",
            message=(
                f"{claimed_engagement.title} has been accepted "
                "and is now being scoped."
            ),
            engagement_id=claimed_engagement.id,
            metadata={
                "status": EngagementStatus.SCOPING.value,
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


    @staticmethod
    async def assign_pentester(
        db: AsyncSession,
        engagement_id: UUID,
        service_delivery_id: UUID,
        request: ServiceDeliveryPentesterAssignment,
    ) -> ServiceDeliveryEngagementActionResponse:
        engagement = await ServiceDeliveryService.require_owned_engagement(
            db,
            engagement_id=engagement_id,
            service_delivery_id=service_delivery_id,
        )

        if engagement.status != EngagementStatus.SCOPING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A pentester can only be assigned while the engagement is in scoping.",
            )

        pentester = await EngagementRepository.get_user_by_id(
            db,
            user_id=request.pentester_id,
        )

        if pentester is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pentester not found.",
            )

        if pentester.role != "pentester":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The selected user is not a pentester.",
            )

        profile = await PentesterProfileRepository.get_by_user_id(
            db,
            user_id=pentester.id,
        )

        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The selected pentester does not have a pentester profile.",
            )

        if not profile.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The selected pentester is inactive.",
            )

        if profile.availability_status == "unavailable":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The selected pentester is unavailable",
            )

        if engagement.assessment_type not in profile.specialisations:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The selected pentester does not support this assessment type.",
            )

        previous_pentester_id = engagement.assigned_to

        assessment_type = engagement.assessment_type.value
        pentester_id = pentester.id

        engagement = await EngagementRepository.update_fields(
            db,
            engagement=engagement,
            changes={
                "assigned_to": pentester_id,
            },
        )

        #enable state change    
        await PentesterProfileRepository.update_availability_status(
            db,
            user_id=pentester_id,
            availability_status="engaged",
        )

        response = ServiceDeliveryService.action_response(
            engagement,
        )

        await AuditRepository.create_log(
            db,
            user_id=service_delivery_id,
            action="engagement.pentester_assigned",
            entity_type="engagement",
            entity_id=engagement.id,
            metadata={
                "previous_pentester_id": (
                    str(previous_pentester_id)
                    if previous_pentester_id is not None
                    else None
                ),
                "pentester_id": str(pentester_id),
                "assessment_type": assessment_type,
            },
        )

        await NotificationService.notify(
            db,
            recipient_id=pentester_id,
            actor_id=service_delivery_id,
            notification_type=NotificationType.ENGAGEMENT_ASSIGNED,
            title="New engagement assignment",
            message=f"You have been assigned to {engagement.title}.",
            engagement_id=engagement.id,
            metadata={
                "assessment_type": assessment_type,
            }
        )

        return response


    @staticmethod
    async def require_eligible_pentester(
        db: AsyncSession,
        pentester_id: UUID,
        assessment_type: AssessmentType,
    ) -> User:
        pentester = await EngagementRepository.get_user_by_id(
            db,
            user_id=pentester_id,
        )

        if pentester is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pentester not found.",
            )

        if pentester.role != "pentester":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The selected user is not a pentester.",
            )

        profile = await PentesterProfileRepository.get_by_user_id(
            db,
            user_id=pentester.id,
        )

        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The selected pentester does not have a profile.",
            )

        if not profile.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Pentester is not active.",
            )

        if profile.availability_status == "unavailable":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The selected pentester is unavailable.",
            )

        if assessment_type not in profile.specialisations:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The selected pentester does not support this assessment type.",
            )

        return pentester

    @staticmethod
    async def release_pentester_if_idle(
        db: AsyncSession,
        pentester_id: UUID,
        exclude_engagement_id: UUID | None = None,
    ) -> None:
        remaining = await PentesterProfileRepository.count_active_engagements(
            db,
            pentester_id=pentester_id,
            exclude_engagement_id=exclude_engagement_id,
        )

        if remaining > 0:
            return
        profile = await PentesterProfileRepository.get_by_user_id(
            db,
            user_id=pentester_id,
        )

        if profile is not None and profile.availability_status == "engaged":
            await PentesterProfileRepository.update_availability_status(
                db,
                user_id=pentester_id,
                availability_status="available",
            )



    
    @staticmethod
    async def schedule_engagement(
        db: AsyncSession,
        engagement_id: UUID,
        service_delivery_id: UUID,
        request: ServiceDeliveryScheduleRequest,
    ) -> ServiceDeliveryEngagementActionResponse:

        engagement = await ServiceDeliveryService.require_owned_engagement(
            db,
            engagement_id=engagement_id,
            service_delivery_id=service_delivery_id,
        )

        if engagement.status != EngagementStatus.SCOPING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only engagements in scoping can be scheduled.",
            )

        if request.scheduled_start_date < date.today():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Scheduled start date cannot be in the past.",
            )

        if engagement.assigned_to is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A pentester must be assigned before scheduling.",
            )

        if engagement.final_quote is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A final quote must be set before scheduling.",
            )

        if not engagement.scope or not engagement.scope.strip():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Engagement scope must be confirmed before scheduling.",
            )

        pentester = await ServiceDeliveryService.require_eligible_pentester(
            db,
            pentester_id=engagement.assigned_to,
            assessment_type=engagement.assessment_type,
        )

        if pentester is None or pentester.role != "pentester":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The assigned pentester is no longer valid.",
            )

        profile = await PentesterProfileRepository.get_by_user_id(
            db,
            user_id=pentester.id,
        )

        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The assigned pentester does not have a profile.",
            )

        if not profile.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The assigned pentester is inactive.",
            )

        if profile.availability_status == "unavailable":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The assigned pentester is unavailable.",
            )

        if engagement.assessment_type not in profile.specialisations:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The assigned pentester does not support this assessment type.",
            )

        has_conflict = await EngagementRepository.has_schedule_conflict(
            db,
            pentester_id=engagement.assigned_to,
            scheduled_start_date=request.scheduled_start_date,
            scheduled_end_date=request.scheduled_end_date,
            exclude_engagement_id=engagement.id,
        )

        if has_conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The assigned pentester has a scheduling conflict.",
            )

        previous_status = engagement.status

        engagement = await EngagementRepository.update_fields(
            db,
            engagement=engagement,
            changes={
                "scheduled_start_date": request.scheduled_start_date,
                "scheduled_end_date": request.scheduled_end_date,
                "status": EngagementStatus.SCHEDULED,
            },
        )

        response = ServiceDeliveryService.action_response(
            engagement,
        )

        await AuditRepository.create_log(
            db,
            user_id=service_delivery_id,
            action="engagement.scheduled",
            entity_type="engagement",
            entity_id=engagement.id,
            metadata={
                "previous_status": previous_status.value,
                "new_status": EngagementStatus.SCHEDULED.value,
                "pentester_id": str(engagement.assigned_to),
                "scheduled_start_date": str(request.scheduled_start_date),
                "scheduled_end_date": str(request.scheduled_end_date),
            },
        )

        notification_metadata={
            "scheduled_start_date": str(request.scheduled_start_date),
            "scheduled_end_date": str(request.scheduled_end_date),
        }

        await NotificationService.notify(
            db,
            recipient_id=engagement.requested_by,
            actor_id=service_delivery_id,
            notification_type=NotificationType.ENGAGEMENT_SCHEDULED,
            title="Engagement scheduled",
            message=(
                f"{engagement.title} has been scheduled for "
                f"{request.scheduled_start_date} to "
                f"{request.scheduled_end_date}."
            ),
            engagement_id=engagement.id,
            metadata=notification_metadata,
        )

        await NotificationService.notify(
            db,
            recipient_id=engagement.assigned_to,
            actor_id=service_delivery_id,
            notification_type=NotificationType.ENGAGEMENT_SCHEDULED,
            title="Engagement scheduled",
            message=(
                f"{engagement.title} has been scheduled for "
                f"{request.scheduled_start_date} to "
                f"{request.scheduled_end_date}."
            ),
            engagement_id=engagement.id,
            metadata=notification_metadata,
        )

        return response


    @staticmethod
    async def reassign_pentester(
        db: AsyncSession,
        engagement_id: UUID,
        service_delivery_id: UUID,
        request: ServiceDeliveryReassignRequest,
    ) -> ServiceDeliveryEngagementActionResponse:

        engagement = await ServiceDeliveryService.require_owned_engagement(
            db,
            engagement_id=engagement_id,
            service_delivery_id=service_delivery_id,
        )

        if engagement.status != EngagementStatus.SCHEDULED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only scheduled engagements can have a pentester reassigned.",
            )

        if engagement.assigned_to is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No pentester currently assigned.",
            )

        if request.pentester_id == engagement.assigned_to:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The selected pentester is already assigned to this engagement.",
            )

        pentester = await ServiceDeliveryService.require_eligible_pentester(
            db,
            pentester_id=request.pentester_id,
            assessment_type=engagement.assessment_type,
        )

        if pentester is None or pentester.role != "pentester":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The assigned pentester is no longer valid.",
            )

        profile = await PentesterProfileRepository.get_by_user_id(
            db,
            user_id=pentester.id,
        )

        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The assigned pentester does not have a profile.",
            )

        if not profile.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The assigned pentester is inactive.",
            )

        if profile.availability_status == "unavailable":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The assigned pentester is unavailable.",
            )

        if engagement.assessment_type not in profile.specialisations:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The assigned pentester does not support this assessment type.",
            )

        if (
            engagement.scheduled_start_date is None 
            or engagement.scheduled_end_date is None
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The engagement does not have valid scheduled dates.",
            )

        has_conflict = await EngagementRepository.has_schedule_conflict(
            db,
            pentester_id=pentester.id,
            scheduled_start_date=engagement.scheduled_start_date,
            scheduled_end_date=engagement.scheduled_end_date,
            exclude_engagement_id=engagement.id,
        )

        if has_conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The assigned pentester has a scheduling conflict.",
            )

        previous_pentester_id = engagement.assigned_to

        engagement = await EngagementRepository.update_fields(
            db,
            engagement=engagement,
            changes={
                "assigned_to": pentester.id,
            },
        )

        await PentesterProfileRepository.update_availability_status(
            db,
            user_id=pentester.id,
            availability_status="engaged",
        )
        if previous_pentester_id is not None:
            await ServiceDeliveryService.release_pentester_if_idle(
                db,
                pentester_id=previous_pentester_id,
                exclude_engagement_id=engagement.id,
            )

        response = ServiceDeliveryService.action_response(
            engagement,
        )

        await AuditRepository.create_log(
            db,
            user_id=service_delivery_id,
            action="engagement.pentester_reassigned",
            entity_type="engagement",
            entity_id=engagement.id,
            metadata={
                "previous_pentester_id": str(previous_pentester_id),
                "new_pentester_id": str(pentester.id),
                "reason": request.reason.strip(),
            },
        )

        await NotificationService.notify(
            db,
            recipient_id=previous_pentester_id,
            actor_id=service_delivery_id,
            notification_type=NotificationType.ENGAGEMENT_REASSIGNED,
            title="Engagement reassigned",
            message=f"You are no longer assigned to {engagement.title}.",
            engagement_id=engagement.id,
            metadata={
                "assignment": "removed",
            },
        )

        await NotificationService.notify(
            db,
            recipient_id=pentester.id,
            actor_id=service_delivery_id,
            notification_type=NotificationType.ENGAGEMENT_REASSIGNED,
            title="New engagement assignment",
            message=f"You have been assigned to {engagement.title}.",
            engagement_id=engagement.id,
            metadata={
                "assignment": "assigned",
            },
        )   

        return response

    
    @staticmethod
    async def reschedule_engagement(
        db: AsyncSession,
        engagement_id: UUID,
        service_delivery_id: UUID,
        request: ServiceDeliveryRescheduleRequest,
    ) -> ServiceDeliveryEngagementActionResponse:

        engagement = await ServiceDeliveryService.require_owned_engagement(
            db,
            engagement_id=engagement_id,
            service_delivery_id=service_delivery_id,
        )

        if engagement.status != EngagementStatus.SCHEDULED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only scheduled engagements can be rescheduled.",
            )

        if request.scheduled_start_date < date.today():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Scheduled start date cannot be in the past.",
            )

        if engagement.assigned_to is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The engagement does not have an assigned pentester.",
            )

        if (
            engagement.scheduled_start_date == request.scheduled_start_date 
            and engagement.scheduled_end_date == request.scheduled_end_date
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The engagement is already scheduled for these dates.",
            )

        await ServiceDeliveryService.require_eligible_pentester(
            db,
            pentester_id=engagement.assigned_to,
            assessment_type=engagement.assessment_type,
        )

        has_conflict = await EngagementRepository.has_schedule_conflict(
            db,
            pentester_id=engagement.assigned_to,
            scheduled_start_date=request.scheduled_start_date,
            scheduled_end_date=request.scheduled_end_date,
            exclude_engagement_id=engagement.id,
        )

        if has_conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The assigned pentester has a scheduling conflict.",
            )

        previous_start_date = engagement.scheduled_start_date
        previous_end_date = engagement.scheduled_end_date

        engagement = await EngagementRepository.update_fields(
            db,
            engagement=engagement,
            changes={
                "scheduled_start_date": request.scheduled_start_date,
                "scheduled_end_date": request.scheduled_end_date,
            },
        )

        response = ServiceDeliveryService.action_response(
            engagement,
        )

        await AuditRepository.create_log(
            db,
            user_id=service_delivery_id,
            action="engagement.rescheduled",
            entity_type="engagement",
            entity_id=engagement.id,
            metadata={
                "previous_start_date": (
                    str(previous_start_date)
                    if previous_start_date is not None
                    else None
                ),
                "previous_end_date": (
                    str(previous_end_date)
                    if previous_end_date is not None
                    else None
                ),
                "new_start_date": str(request.scheduled_start_date),
                "new_end_date": str(request.scheduled_end_date),
                "pentester_id": str(engagement.assigned_to),
                "reason": request.reason
            },
        )

        notification_metadata = {
            "previous_start_date": (
                str(previous_start_date)
                if previous_start_date is not None
                else None
            ),
            "previous_end_date": (
                str(previous_end_date)
                if previous_end_date is not None
                else None
            ),
            "scheduled_start_date": str(request.scheduled_start_date),
            "scheduled_end_date": str(request.scheduled_end_date),
        }

        notification_message = (
            f"{engagement.title} has been rescheduled to "
            f"{request.scheduled_start_date} to "
            f"{request.scheduled_end_date}."
        )

        await NotificationService.notify(
            db,
            recipient_id=engagement.requested_by,
            actor_id=service_delivery_id,
            notification_type=NotificationType.ENGAGEMENT_RESCHEDULED,
            title="Engagement rescheduled",
            message=notification_message,
            engagement_id=engagement.id,
            metadata=notification_metadata
        )

        await NotificationService.notify(
            db,
            recipient_id=engagement.assigned_to,
            actor_id=service_delivery_id,
            notification_type=NotificationType.ENGAGEMENT_RESCHEDULED,
            title="Engagement rescheduled",
            message=notification_message,
            engagement_id=engagement.id,
            metadata=notification_metadata
        )

        return response


    @staticmethod
    async def return_from_review(
        db: AsyncSession,
        engagement_id: UUID,
        service_delivery_id: UUID,
        request: ServiceDeliveryReviewReturnRequest
    ) -> ServiceDeliveryEngagementActionResponse:
        
        engagement = await ServiceDeliveryService.require_owned_engagement(
            db,
            engagement_id=engagement_id,
            service_delivery_id=service_delivery_id,
        )

        if engagement.status != EngagementStatus.REVIEW:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only engagements in review can be returned to the pentester.",
            )
        
        if engagement.assigned_to is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The engagement does not have an assigned pentester.",
            )

        reviewed_at = datetime.now(timezone.utc)

        engagement = await EngagementRepository.update_fields(
            db,
            engagement=engagement,
            changes={
                "status": EngagementStatus.IN_PROGRESS,
                "reviewed_by": service_delivery_id,
                "reviewed_at": reviewed_at,
                "review_note": request.review_note,
            },
        )

        response = ServiceDeliveryService.action_response(
            engagement,
        )

        await AuditRepository.create_log(
            db,
            user_id=service_delivery_id,
            action="engagement.returned_to_pentester",
            entity_type="engagement",
            entity_id=engagement.id,
            metadata={
                "previous_status": EngagementStatus.REVIEW.value,
                "new_status": EngagementStatus.IN_PROGRESS.value,
                "pentester_id": str(engagement.assigned_to),
                "review_note": request.review_note,
            },
        )

        await NotificationService.notify(
            db,
            recipient_id=engagement.assigned_to,
            actor_id=service_delivery_id,
            notification_type=NotificationType.ENGAGEMENT_REVIEW_RETURNED,
            title="Engagement returned for changes",
            message=f"{engagement.title} requires further changes.",
            engagement_id=engagement.id,
            metadata={
                "status": EngagementStatus.IN_PROGRESS.value,
            },
        )

        return response


    @staticmethod
    async def complete_review(
        db: AsyncSession,
        engagement_id: UUID,
        service_delivery_id: UUID,
    ) -> ServiceDeliveryEngagementActionResponse:
        
        engagement = await ServiceDeliveryService.require_owned_engagement(
            db,
            engagement_id=engagement_id,
            service_delivery_id=service_delivery_id,
        )

        if engagement.status != EngagementStatus.REVIEW:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only engagements in review can be completed.",
            )

        report = await get_latest_for_engagement(
            db,
            engagement_id=engagement.id,
        )


        if report is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Final report is not ready",
            )

        if report.status != ReportStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Final report is not ready.",
            )

        report_storage_ref = report.pdf_path
        report_id = report.id
        report_version = report.version

        completed_at = datetime.now(timezone.utc)

        engagement = await EngagementRepository.update_fields(
            db,
            engagement=engagement,
            changes={
                "status": EngagementStatus.COMPLETED,
                "reviewed_by": service_delivery_id,
                "reviewed_at": completed_at,
                "completed_at": completed_at,
            },
        )
        
        if engagement.assigned_to is not None:
            await ServiceDeliveryService.release_pentester_if_idle(
                db,
                pentester_id=engagement.assigned_to,
            )

        response = ServiceDeliveryService.action_response(
            engagement,
        )

        await AuditRepository.create_log(
            db,
            user_id=service_delivery_id,
            action="engagement.completed",
            entity_type="engagement",
            entity_id=engagement.id,
            metadata={
                "previous_status": EngagementStatus.REVIEW.value,
                "new_status": EngagementStatus.COMPLETED.value,
                "report_id": str(report_id),
                "report_version": report_version,
            },
        )


        await NotificationService.notify(
            db,
            recipient_id=engagement.requested_by,
            actor_id=service_delivery_id,
            notification_type=NotificationType.ENGAGEMENT_COMPLETED,
            title="Penetration test completed",
            message=f"{engagement.title} has been completed.",
            engagement_id=engagement.id,
            metadata={
                "status": EngagementStatus.COMPLETED.value,
                "report_id": str(report_id),
            },
        )

        await NotificationService.notify(
            db,
            recipient_id=engagement.assigned_to,
            actor_id=service_delivery_id,
            notification_type=NotificationType.ENGAGEMENT_COMPLETED,
            title="Engagement completed",
            message=f"{engagement.title} has completed review.",
            engagement_id=engagement.id,
            metadata={
                "status": EngagementStatus.COMPLETED.value,
            },
        )

        client = await EngagementRepository.get_user_by_id(
            db,
            user_id=engagement.requested_by,
        )

        if client is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Engagement client could not be found",
            )

        send_engagement_report_email_task.delay(
            client.email,
            engagement.title,
            report_storage_ref,
        )
        
        return response


    @staticmethod
    async def cancel_engagement(
        db: AsyncSession,
        engagement_id: UUID,
        service_delivery_id: UUID,
        request: ServiceDeliveryCancelRequest
    ) -> ServiceDeliveryEngagementActionResponse:
        
        engagement = await ServiceDeliveryService.require_engagement(
            db,
            engagement_id=engagement_id,
        )

        cancellable_statuses = {
            EngagementStatus.REQUESTED,
            EngagementStatus.SCOPING,
            EngagementStatus.SCHEDULED,
            EngagementStatus.IN_PROGRESS,
        }

        if engagement.status not in cancellable_statuses:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This engagement can no longer be cancelled.",
            )
        
        if (
            engagement.service_delivery_id is not None
            and engagement.service_delivery_id != service_delivery_id
        ):
            raise HTTPException(
                status_code = status.HTTP_403_FORBIDDEN,
                detail="This engagement is not assigned to you.",
            )

        previous_status = engagement.status

        engagement = await EngagementRepository.update_fields(
            db,
            engagement=engagement,
            changes={
                "status": EngagementStatus.CANCELLED,
            },
        )	
        if engagement.assigned_to is not None:
            await ServiceDeliveryService.release_pentester_if_idle(
                db,
                pentester_id=engagement.assigned_to,
            )

        response = ServiceDeliveryService.action_response(
            engagement,
        )

        await AuditRepository.create_log(
            db,
            user_id=service_delivery_id,
            action="engagement.cancelled",
            entity_type="engagement",
            entity_id=engagement.id,
            metadata={
                "previous_status": previous_status.value,
                "new_status": EngagementStatus.CANCELLED.value,
                "reason": request.reason,
            },
        )

        await NotificationService.notify(
            db,
            recipient_id=engagement.requested_by,
            actor_id=service_delivery_id,
            notification_type=NotificationType.ENGAGEMENT_CANCELLED,
            title="Engagement cancelled",
            message=f"{engagement.title} has been cancelled.",
            engagement_id=engagement.id,
            metadata={
                "previous_status": previous_status.value,
            },
        )

        await NotificationService.notify(
            db,
            recipient_id=engagement.assigned_to,
            actor_id=service_delivery_id,
            notification_type=NotificationType.ENGAGEMENT_CANCELLED,
            title="Engagement cancelled",
            message=f"{engagement.title} has been cancelled.",
            engagement_id=engagement.id,
            metadata={
                "previous_status": previous_status.value,
            },
        )

        return response


    @staticmethod
    def dashboard_engagement(
        engagement: Engagement,
        client: User,
        service_delivery: User | None,
        pentester: User | None,
    ) -> ServiceDeliveryDashboardEngagement:
        return ServiceDeliveryDashboardEngagement(
            id=engagement.id,
            title=engagement.title,
            status=engagement.status,
            assessment_type=engagement.assessment_type,
            priority=engagement.priority,
            client=ServiceDeliveryService.user_summary(client),
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
            scheduled_start_date=engagement.scheduled_start_date,
            scheduled_end_date=engagement.scheduled_end_date,
            updated_at=engagement.updated_at,
        )


    @staticmethod
    async def get_dashboard(
        db: AsyncSession
    ) -> ServiceDeliveryDashboardResponse:
        counts = await EngagementRepository.get_service_delivery_dashboard_counts(db)

        unclaimed_rows = (
            await EngagementRepository.list_for_service_delivery_dashboard(
                db,
                engagement_status=EngagementStatus.REQUESTED,
                unclaimed_only=True,
                limit=5,
            )
        )

        review_rows = (
            await EngagementRepository.list_for_service_delivery_dashboard(
                db,
                engagement_status=EngagementStatus.REVIEW,
                limit=5,
            )
        )

        upcoming_rows = (
            await EngagementRepository.list_for_service_delivery_dashboard(
                db,
                engagement_status=EngagementStatus.SCHEDULED,
                limit=5,
            )
        )

        return ServiceDeliveryDashboardResponse(
            counts=ServiceDeliveryDashboardCounts(
                requested=counts[EngagementStatus.REQUESTED],
                scoping=counts[EngagementStatus.SCOPING],
                scheduled=counts[EngagementStatus.SCHEDULED],
                in_progress=counts[EngagementStatus.IN_PROGRESS],
                review=counts[EngagementStatus.REVIEW],
                completed=counts[EngagementStatus.COMPLETED],
                cancelled=counts[EngagementStatus.CANCELLED],
                needs_attention=(
                    counts[EngagementStatus.REQUESTED] 
                    + counts[EngagementStatus.REVIEW]
                ),
            ),
            unclaimed_requests=[
                ServiceDeliveryService.dashboard_engagement(
                    engagement,
                    client,
                    service_delivery,
                    pentester,
                ) 
                for engagement, client, service_delivery, pentester
                in unclaimed_rows
            ],
            awaiting_review=[
                ServiceDeliveryService.dashboard_engagement(
                    engagement,
                    client,
                    service_delivery,
                    pentester
                )
                for engagement, client, service_delivery, pentester
                in review_rows
            ],
            upcoming_engagements=[
                ServiceDeliveryService.dashboard_engagement(
                    engagement,
                    client,
                    service_delivery,
                    pentester
                )
                for engagement, client, service_delivery, pentester
                in upcoming_rows
            ],
        )


    @staticmethod
    async def list_pentesters(
        db: AsyncSession,
        *,
        search: str | None,
        assessment_type: AssessmentType | None,
        availability_status: str | None,
        is_active: bool | None,
        limit: int,
        offset: int,
    ) -> ServiceDeliveryPentesterListResponse:

        rows, total = await PentesterProfileRepository.list_for_service_delivery(
            db,
            search=search,
            assessment_type=assessment_type,
            availability_status=availability_status,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )

        items = [
            ServiceDeliveryPentesterListItem(
                id=user.id,
                full_name=user.full_name,
                email=user.email,
                is_active=profile.is_active,
                availability_status=profile.availability_status,
                specialisations=profile.specialisations,
                assigned_engagements=assigned_count,
                created_at=user.created_at,
            ) for user, profile, assigned_count in rows
        ]

        return ServiceDeliveryPentesterListResponse(
            items=items,
            pagination=EngagementPagination(
                total=total,
                limit=limit,
                offset=offset,
                has_more=offset + len(items) < total,
            ),
        )


    @staticmethod
    async def get_pentester(
        db: AsyncSession,
        pentester_id: UUID,
    ) -> ServiceDeliveryPentesterDetail:

        pentester = await EngagementRepository.get_user_by_id(
            db,
            user_id=pentester_id,
        )

        if pentester is None or pentester.role != "pentester":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pentester not found.",
            )

        profile = await PentesterProfileRepository.get_by_user_id(
            db,
            user_id=pentester_id,
        )

        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pentester profile not found.",
            )

        counts = await PentesterProfileRepository.get_engagement_counts(
            db,
            pentester_id=pentester.id,
        )

        assigned_engagements = (
            counts[EngagementStatus.SCHEDULED]
            + counts[EngagementStatus.IN_PROGRESS]
            + counts[EngagementStatus.REVIEW]
        )

        return ServiceDeliveryPentesterDetail(
            id=pentester.id,
            full_name=pentester.full_name,
            email=pentester.email,
            is_active=profile.is_active,
            availability_status=profile.availability_status,
            specialisations=profile.specialisations,
            assigned_engagements=assigned_engagements,
            scheduled_engagements=counts[EngagementStatus.SCHEDULED],
            in_progress_engagements=counts[EngagementStatus.IN_PROGRESS],
            created_at=pentester.created_at,
        )


    @staticmethod
    async def require_findings_visible_engagement(
        db: AsyncSession,
        engagement_id: UUID,
        service_delivery_id: UUID,
    ) -> Engagement:
        engagement = await ServiceDeliveryService.require_owned_engagement(
            db,
            engagement_id=engagement_id,
            service_delivery_id=service_delivery_id,
        )

        allowed_statuses = {
            EngagementStatus.IN_PROGRESS,
            EngagementStatus.REVIEW,
            EngagementStatus.COMPLETED,
        }

        if engagement.status not in allowed_statuses:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Findings are not available for this engagement.",
            )

        return engagement


    @staticmethod
    async def list_findings(
        db: AsyncSession,
        *,
        engagement_id: UUID,
        service_delivery_id: UUID,
        severity: Severity | None,
        finding_status: FindingStatus | None,
        limit: int,
        offset: int,
    ) -> ServiceDeliveryFindingListResponse:
        await ServiceDeliveryService.require_findings_visible_engagement(
            db,
            engagement_id=engagement_id,
            service_delivery_id=service_delivery_id,
        )

        findings, total = await FindingRepository.list_by_engagement(
            db,
            engagement_id=engagement_id,
            source=None,
            severity=severity,
            finding_status=finding_status,
            search=None,
            limit=limit,
            offset=offset,
        )

        items = [
            ServiceDeliveryFindingListItem(
                id=finding.id,
                title=finding.title,
                severity=finding.severity,
                status=finding.status,
                engagement_asset_id=finding.engagement_asset_id,
                asset_identifier=asset_identifier,
                source=finding.source,
                is_verified=finding.is_verified,
                cvss_score=finding.cvss_score,
                cve_id=finding.cve_id,
                created_at=finding.created_at,
            ) for finding, asset_identifier in findings
        ]

        return ServiceDeliveryFindingListResponse(
            items=items,
            pagination=EngagementPagination(
                total=total,
                limit=limit,
                offset=offset,
                has_more=offset + len(items) < total,
            )
        )


    @staticmethod
    async def get_finding(
        db: AsyncSession,
        *,
        engagement_id: UUID,
        finding_id: UUID,
        service_delivery_id: UUID,
    ) -> ServiceDeliveryFindingDetail:

        await ServiceDeliveryService.require_findings_visible_engagement(
            db,
            engagement_id=engagement_id,
            service_delivery_id=service_delivery_id,
        )

        finding = await FindingRepository.get_by_id_and_engagement(
            db,
            finding_id=finding_id,
            engagement_id=engagement_id,
        )

        if finding is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Finding not found.",
            )

        asset_identifier = None

        if finding.engagement_asset_id is not None:
            asset = await EngagementRepository.get_asset_by_id(
                db,
                engagement_id=engagement_id,
                asset_id=finding.engagement_asset_id,
            )

            if asset is not None:
                asset_identifier = asset.identifier

        return ServiceDeliveryFindingDetail(
            id=finding.id,
            engagement_id=engagement_id,
            engagement_asset_id=finding.engagement_asset_id,
            asset_identifier=asset_identifier,
            source=finding.source,
            title=finding.title,
            description=finding.description,
            recommendation=finding.recommendation,
            severity=finding.severity,
            status=finding.status,
            is_verified=finding.is_verified,
            cvss_score=finding.cvss_score,
            cve_id=finding.cve_id,
            created_by=finding.created_by,
            created_at=finding.created_at,
        )


    @staticmethod
    async def get_evidence_for_download(
        db: AsyncSession,
        evidence_id: UUID,
        service_delivery_id: UUID,
    ) -> EvidenceFile:

        evidence = await FindingRepository.get_evidence_by_id(
            db,
            evidence_id=evidence_id,
        )

        if evidence is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evidence file not found.",
            )

        finding = await FindingRepository.get_by_id(
            db,
            finding_id=evidence.finding_id,
        )

        if finding is None or finding.engagement_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evidence file not found.",
            )

        await ServiceDeliveryService.require_findings_visible_engagement(
            db,
            engagement_id=finding.engagement_id,
            service_delivery_id=service_delivery_id,
        )

        return evidence

    @staticmethod
    async def require_retests_visible_engagement(
        db: AsyncSession,
        engagement_id: UUID,
        service_delivery_id: UUID,
    ) -> Engagement:
        engagement = await ServiceDeliveryService.require_owned_engagement(
            db,
            engagement_id=engagement_id,
            service_delivery_id=service_delivery_id,
        )

        if engagement.status != EngagementStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Retests are only available for complete engagements.",
            )

        return engagement


    @staticmethod
    async def list_retests(
        db: AsyncSession,
        engagement_id: UUID,
        service_delivery_id: UUID,
    ) -> RetestListResponse:
        await ServiceDeliveryService.require_retests_visible_engagement(
            db,
            engagement_id=engagement_id,
            service_delivery_id=service_delivery_id,
        )

        retests = await RetestRepository.list_by_engagement(
            db,
            engagement_id=engagement_id,
        )

        return RetestListResponse(
            items=[
                RetestListItem(
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
                ) for retest in retests
            ]
        )


    @staticmethod
    async def get_retest(
        db: AsyncSession,
        retest_id: UUID,
        service_delivery_id: UUID,
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

        engagement_id = retest.finding.engagement_id

        await ServiceDeliveryService.require_retests_visible_engagement(
            db,
            engagement_id=engagement_id,
            service_delivery_id=service_delivery_id,
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


    @staticmethod
    async def get_message_conversations(
        db: AsyncSession,
        service_delivery_id: UUID,
    ) -> ServiceDeliveryConversationListResponse:

        rows = await EngagementRepository.get_service_delivery_conversation_summaries(
            db,
            service_delivery_id=service_delivery_id,
        )

        items: list[ServiceDeliveryConversationSummary] = []

        for (
            engagement,
            channel,
            participant,
            latest_comment,
            sender,
            message_count,
            unread_count,
        ) in rows:
            last_message = None

            if latest_comment is not None:
                last_message = LatestMessageSummary(
                    id=latest_comment.id,
                    comment=latest_comment.comment,
                    sender_name=(
                        sender.full_name
                        if sender is not None
                        else None
                    ),
                    sender_role=(
                        sender.role
                        if sender is not None
                        else "unknown"
                    ),
                    created_at=latest_comment.created_at,
                )

            items.append(
                ServiceDeliveryConversationSummary(
                    engagement_id=engagement.id,
                    engagement_title=engagement.title,
                    channel=channel,
                    participant=MessageClientSummary(
                        id=participant.id,
                        full_name=participant.full_name,
                        email=participant.email,
                    ),
                    last_message=last_message,
                    message_count=message_count,
                    unread_count=unread_count,
                )
            )

        return ServiceDeliveryConversationListResponse(items=items)


    @staticmethod
    async def list_audit(
        db: AsyncSession,
        service_delivery_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> ActivityListResponse:

        logs = await AuditRepository.list_for_service_delivery(
            db,
            service_delivery_id=service_delivery_id,
            limit=limit,
            offset=offset,
        )

        users = await EngagementRepository.get_users_by_ids(
            db,
            user_ids={
                log.user_id
                for log in logs
                if log.user_id is not None
            },
        )

        return ActivityListResponse(
            items=[
                ActivityItemResponse(
                    id=log.id,
                    action=log.action,
                    entity_type=log.entity_type,
                    entity_id=log.entity_id,
                    actor=(
                        UserSummary(
                            id=users[log.user_id].id,
                            full_name=users[log.user_id].full_name,
                            email=users[log.user_id].email,
                            role=users[log.user_id].role,
                        )
                        if (
                            log.user_id is not None
                            and log.user_id in users
                        ) else None
                    ),
                    metadata=log.metadata_,
                    created_at=log.created_at,
                ) for log in logs
            ]
        )


    @staticmethod
    async def create_pentester(
        db: AsyncSession,
        service_delivery_user_id: UUID,
        request: ServiceDeliveryPentesterCreate,
    ) -> ServiceDeliveryPentesterDetail:
        normalized_email = str(request.email).strip().lower()
        normalized_name = request.full_name.strip()

        existing_user = await UserRepository.get_by_email(
            db,
            email=normalized_email,
        )

        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email address already exists.",
            )

        keycloak = KeycloakAdminService()

        try:
            provider_user_id = await keycloak.create_pentester(
                email=normalized_email,
                full_name=normalized_name,
            )

        except KeycloakAdminError as err:
            if err.status_code == status.HTTP_409_CONFLICT:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A Keycloak user with this email address already exists.",
                ) from err

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to create the pentester account in Keycloak.",
            ) from err

        except RuntimeError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Keycloak provisioning is not configured.",
            )

        try:
            await keycloak.assign_pentester_role(provider_user_id)

        except KeycloakAdminError:
            try:
                await keycloak.delete_user(provider_user_id)
            except KeycloakAdminError:
                logger.exception(
                    "Failed to clean up Keycloak user %s.",
                    provider_user_id,
                )

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to assign the pentester role in Keycloak.",
            )

        try:
            pentester = await UserRepository.create_pentester(
                db,
                provider_id=provider_user_id,
                email=normalized_email,
                full_name=normalized_name,
            )

            profile = await PentesterProfileRepository.create_profile(
                db,
                user_id=pentester.id,
                specialisations=request.specialisations,
            )

            pentester_id = pentester.id
            pentester_email = pentester.email

            specialisations = [
                specialisation.value
                for specialisation in profile.specialisations
            ]

            await AuditRepository.create_log(
                db,
                user_id=service_delivery_user_id,
                action="pentester.created",
                entity_type="user",
                entity_id=pentester_id,
                metadata={
                    "email": pentester_email,
                    "keycloak_user_id": provider_user_id,
                    "specialisations": specialisations,
                },
            )

        except Exception:
            await db.rollback()

            try:
                await keycloak.delete_user(provider_user_id)

            except KeycloakAdminError:
                logger.exception(
                    "Failed to clean up Keycloak user %s after DB failure.",
                    provider_user_id,
                )

            raise

        try:
            await keycloak.send_activation_email(provider_user_id)

        except KeycloakAdminError:
            logger.exception(
                "Pentester %s was created but activation email failed.",
                pentester_id,
            )

        return await ServiceDeliveryService.get_pentester(
            db,
            pentester_id=pentester_id,
        )


    @staticmethod
    async def deactivate_pentester(
        db: AsyncSession,
        service_delivery_user_id: UUID,
        pentester_id: UUID,
    ) -> ServiceDeliveryPentesterDetail:
        pentester = await EngagementRepository.get_user_by_id(
            db,
            user_id=pentester_id,
        )

        if pentester is None or pentester.role != "pentester":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pentester not found.",
            )

        profile = await PentesterProfileRepository.get_by_user_id(
            db,
            user_id=pentester.id,
        )

        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pentester profile not found.",
            )

        pentester_id = pentester.id
        pentester_email = pentester.email
        provider_user_id = pentester.auth_provider_id

        if profile.is_active:
            profile.is_active = False
            await db.commit()
            await db.refresh(profile)

        try:
            keycloak = KeycloakAdminService()

            await keycloak.disable_user(provider_user_id)

        except KeycloakAdminError as err:
            logger.exception(
                "Pentester %s was deactivated locally but Keycloak disable failed.",
                pentester_id,
            )

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The pentester was deactivated in PenFlow, " \
                "but Keycloak could not be updated.",
            ) from err

        except RuntimeError as err:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The pentester was deactivated in PenFlow, " \
                "but Keycloak provisioning is not configured.",
            ) from err

        await AuditRepository.create_log(
            db,
            user_id=service_delivery_user_id,
            action="pentester.deactivated",
            entity_type="user",
            entity_id=pentester_id,
            metadata={
                "email": pentester_email,
                "keycloak_user_id": provider_user_id,
            },
        )

        return await ServiceDeliveryService.get_pentester(
            db,
            pentester_id=pentester_id,
        )