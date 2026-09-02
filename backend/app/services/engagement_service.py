from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import EngagementMessageChannel, EngagementStatus, FindingStatus, Severity
from app.models.engagement import Engagement
from app.models.finding import Finding
from app.models.report import Report, ReportStatus
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.engagement_comment_repository import EngagementCommentRepository
from app.repositories.engagement_repository import EngagementRepository
from app.repositories.finding_repository import FindingRepository
from app.repositories.retest_repository import RetestRepository
from app.schemas.engagement import (
    ActivityItemResponse,
    ActivityListResponse,
    EngagementAssetResponse,
    EngagementCounts,
    EngagementCreateRequest,
    EngagementCreateResponse,
    EngagementDetailResponse,
    EngagementListItem,
    EngagementListResponse,
    EngagementMessageCreate,
    EngagementMessageListResponse,
    EngagementMessageResponse,
    EngagementOverviewCounts,
    EngagementPagination,
    EngagementSortField,
    EngagementStatusResponse,
    LatestMessageSummary,
    MarkMessagesReadResponse,
    MessageClientSummary,
    PentesterConversationListResponse,
    PentesterConversationSummary,
    PreviousScanSummary,
    SortOrder,
    UserSummary,
)
from app.schemas.finding import (
    FindingCreate,
    FindingListItem,
    FindingListResponse,
    FindingPagination,
)
from app.schemas.retest import RetestFindingSummary, RetestListItem, RetestListResponse
from app.tasks.report_tasks import render_engagement_report_pdf_task


class EngagementService:
    @staticmethod
    async def require_assigned_engagement(
        db: AsyncSession,
        engagement_id: UUID,
        user_id: UUID,
    ) -> Engagement:
        engagement = await EngagementRepository.get_assigned_by_id(
            db,
            engagement_id=engagement_id,
            user_id=user_id,
        )

        if engagement is None:
            raise HTTPException(
                status_code = status.HTTP_404_NOT_FOUND,
                detail = "Engagement was not found or is not assigned to this user."
            )

        return engagement

    @staticmethod
    async def require_viewable_engagement(
        db: AsyncSession,
        engagement_id: UUID,
        user_id: UUID,
    ) -> Engagement:
        engagement = await EngagementRepository.get_by_id(
            db,
            engagement_id=engagement_id,
        )

        if engagement is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Engagement was not found.",
            )

        user = await EngagementRepository.get_user_by_id(
            db,
            user_id=user_id,
        )

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not present.",
            )

        if (
            engagement.requested_by == user_id
            or engagement.assigned_to == user_id
            or engagement.service_delivery_id == user_id
            or user.role == "admin"
        ):
            return engagement

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Engagement was not found.",
        )

    @staticmethod
    def build_create_response \
                    (
                    engagement: Engagement,
                    asset_count: int,
            ) -> EngagementCreateResponse:
        # confirmation of request for ui
        return EngagementCreateResponse \
                (
                id=engagement.id,
                status=engagement.status,
                engagement_type=engagement.engagement_type,
                assessment_type=engagement.assessment_type,
                objective=engagement.objective or engagement.scope,
                start_date=engagement.requested_start_date,
                end_date=engagement.requested_end_date,
                asset_count=asset_count,
                estimated_quote=engagement.estimated_quote,
                service_delivery_id=engagement.service_delivery_id,
                assigned_pentester_id=engagement.assigned_to,
                created_at=engagement.created_at,
            )

    @staticmethod
    async def require_message_channel_access(
        db: AsyncSession,
        engagement_id: UUID,
        user_id: UUID,
        channel: EngagementMessageChannel,
    ) -> Engagement:
        engagement = await EngagementRepository.get_by_id(
            db,
            engagement_id=engagement_id,
        )

        if engagement is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Engagement not found.",
            )

        if channel == EngagementMessageChannel.CLIENT_SERVICE_DELIVERY:
            allowed = (
                user_id == engagement.requested_by
                or user_id == engagement.service_delivery_id
            )

        elif channel == EngagementMessageChannel.SERVICE_DELIVERY_PENTESTER:
            allowed = (
                user_id == engagement.service_delivery_id
                or user_id == engagement.assigned_to
            )

        else:
            allowed = False

        if not allowed:
            raise HTTPException(
                status_code = status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )

        return engagement


    @staticmethod
    def finding_to_list_item(
        finding: Finding,
        asset_identifier: str | None = None,
    ) -> FindingListItem:
        return FindingListItem(
            id=finding.id,
            engagement_id=finding.engagement_id,
            engagement_asset_id=finding.engagement_asset_id,
            source=finding.source,
            status=finding.status,
            is_verified=finding.is_verified,
            severity=finding.severity,
            cvss_score=finding.cvss_score,
            cve_id=finding.cve_id,
            title=finding.title,
            description=finding.description,
            created_at=finding.created_at,
            asset_identifier=asset_identifier,
        )


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
        user_id: UUID,
        user_role: str,
        engagement_status: EngagementStatus | None,
        search: str | None,
        sort: EngagementSortField,
        order: SortOrder,
        limit: int,
        offset: int,
    ) -> EngagementListResponse:
        rows, total = await EngagementRepository.list_assigned(
            db,
            user_id=user_id,
            user_role=user_role,
            engagement_status=engagement_status,
            search=search,
            sort=sort,
            order=order,
            limit=limit,
            offset=offset,
        )

        status_counts = await EngagementRepository.get_status_counts(
            db,
            user_id=user_id,
            user_role=user_role,
        )

        items = [
            EngagementListItem(
                id=engagement.id,
                title = engagement.title,
                client_name=client_name,
                engagement_type=engagement.engagement_type,
                priority=engagement.priority,
                status=engagement.status,
                asset_count=asset_count,
                requested_start_date=engagement.requested_start_date,
                estimated_duration_days=engagement.estimated_duration_days,
                target_date=EngagementRepository.calc_target_date(
                    engagement.requested_start_date,
                    engagement.estimated_duration_days,
                ),
                updated_at=engagement.updated_at,
                estimated_quote=engagement.estimated_quote,
                assigned_pentester_name=pentester_name,
                user_role=user_role,
            )
            for engagement, client_name, asset_count, pentester_name in rows
        ]

        return EngagementListResponse(
            items=items,
            counts = EngagementCounts(
                all=sum(status_counts.values()),
                requested=status_counts.get(EngagementStatus.REQUESTED, 0),
                scoping=status_counts.get(EngagementStatus.SCOPING, 0),
                scheduled=status_counts.get(EngagementStatus.SCHEDULED, 0),
                in_progress=status_counts.get(EngagementStatus.IN_PROGRESS, 0),
                review=status_counts.get(EngagementStatus.REVIEW, 0),
                completed=status_counts.get(EngagementStatus.COMPLETED, 0),
                cancelled=status_counts.get(EngagementStatus.CANCELLED, 0),
            ),
            pagination=EngagementPagination(
                total=total,
                limit=limit,
                offset=offset,
                has_more = offset + len(items) < total,
            ),
        )


    @staticmethod
    async def get_engagement_detail(
        db: AsyncSession,
        engagement_id: UUID,
        user_id: UUID,
    ) -> EngagementDetailResponse:
        engagement = await EngagementService.require_viewable_engagement(
            db,
            engagement_id=engagement_id,
            user_id=user_id,
        )

        assets = await EngagementRepository.get_assets(
            db,
            engagement_id=engagement_id,
        )

        manual_count, automated_count = (
            await EngagementRepository.get_overview_finding_counts(
                db,
                engagement_id=engagement_id,
            )
        )

        recent_findings = await EngagementRepository.get_recent_findings(
            db,
            engagement_id=engagement_id,
            limit = 5,
        )

        previous_scan_result = await EngagementRepository.get_previous_scan_summary(
            db,
            engagement_id=engagement_id,
        )

        client = await EngagementRepository.get_user_by_id(
            db,
            user_id=engagement.requested_by,
        )

        assigned_pentester = None
        if engagement.assigned_to is not None:
            assigned_pentester = await EngagementRepository.get_user_by_id(
                db,
                user_id=engagement.assigned_to,
            )

        service_delivery = None
        if engagement.service_delivery_id is not None:
            service_delivery = await EngagementRepository.get_user_by_id(
                db,
                user_id=engagement.service_delivery_id,
            )

        if client is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Engagement client could not be found.",
            )

        previous_scan = None

        if previous_scan_result is not None:
            (
                scan_id,
                domain,
                completed_at,
                relevant_findings,
            ) = previous_scan_result

            previous_scan = PreviousScanSummary(
                id=scan_id,
                domain=domain,
                completed_at=completed_at,
                relevant_findings=relevant_findings,
                reviewed_findings=0,
            )

        recent_items = [
            EngagementService.finding_to_list_item(
                finding,
                asset_identifier=asset_identifier,
            )
            for finding, asset_identifier in recent_findings
        ]

        return EngagementDetailResponse(
            id=engagement.id,
            title=engagement.title,
            engagement_type=engagement.engagement_type,
            assessment_type=engagement.assessment_type,
            priority=engagement.priority,
            status=engagement.status,
            scope=engagement.scope,
            estimated_quote=engagement.estimated_quote,
            final_quote=engagement.final_quote,
            estimated_duration_days=engagement.estimated_duration_days,
            requested_start_date=engagement.requested_start_date,
            requested_end_date=engagement.requested_end_date,
            scheduled_start_date=engagement.scheduled_start_date,
            scheduled_end_date=engagement.scheduled_end_date,
            target_date=EngagementRepository.calc_target_date(
                engagement.requested_start_date,
                engagement.estimated_duration_days,
            ),
            started_at=engagement.started_at,
            completed_at=engagement.completed_at,
            reviewed_at=engagement.reviewed_at,
            review_note=engagement.review_note,
            created_at=engagement.created_at,
            updated_at=engagement.updated_at,
            client=EngagementService.user_summary(client),
            service_delivery=(
                EngagementService.user_summary(service_delivery)
                if service_delivery is not None
                else None
            ),
            assigned_pentester=(
                EngagementService.user_summary(assigned_pentester)
                if assigned_pentester is not None
                else None
            ),
            assets=[
                EngagementAssetResponse.model_validate(asset)
                for asset in assets
            ],
            counts=EngagementOverviewCounts(
                assets=len(assets),
                manual_findings=manual_count,
                automated_findings=automated_count,
            ),
            recent_findings=recent_items,
            previous_scan=previous_scan,
        )


    @staticmethod
    async def list_findings(
        db: AsyncSession,
        *,
        engagement_id: UUID,
        user_id: UUID,
        source: str | None,
        severity: Severity | None,
        finding_status: FindingStatus | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> FindingListResponse:
        await EngagementService.require_assigned_engagement(
            db,
            engagement_id=engagement_id,
            user_id=user_id,
        )

        rows, total = await FindingRepository.list_by_engagement(
            db,
            engagement_id=engagement_id,
            source=source,
            severity=severity,
            finding_status=finding_status,
            search=search,
            limit=limit,
            offset=offset,
        )

        items = [
            EngagementService.finding_to_list_item(
                finding,
                asset_identifier=asset_identifier,
            )
            for finding, asset_identifier in rows
        ]

        return FindingListResponse(
            items=items,
            pagination=FindingPagination(
                total=total,
                limit=limit,
                offset=offset,
                has_more=offset + len(items) < total,
            ),
        )

    @staticmethod
    async def create_engagement \
                    (
                    db: AsyncSession,
                    request: EngagementCreateRequest,
                    client_user_id: UUID,
            ) -> EngagementCreateResponse:
        # save the request first.
        engagement = await EngagementRepository.create_engagement \
                (
                db,
                request=request,
                client_user_id=client_user_id,
            )
        return EngagementService.build_create_response \
                (
                engagement,
                asset_count=len(request.assets),
            )

    @staticmethod
    async def create_manual_finding(
        db: AsyncSession,
        engagement_id: UUID,
        user_id: UUID,
        request: FindingCreate,
    ) -> FindingListItem:
        engagement = await EngagementService.require_assigned_engagement(
            db,
            engagement_id=engagement_id,
            user_id=user_id,
        )

        if engagement is None or engagement.status != EngagementStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Findings can only be created while the engagement is in progress.",
            )

        if request.engagement_asset_id is not None:
            asset = await EngagementRepository.get_asset_by_id(
                db,
                engagement_id=engagement_id,
                asset_id=request.engagement_asset_id,
            )

            if asset is None:
                raise HTTPException(
                    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="The selected asset does not belong to this engagement."
                )

        finding = await FindingRepository.create_manual_finding(
            db,
            engagement_id=engagement_id,
            created_by=user_id,
            request=request,
        )

        await AuditRepository.create_log(
            db,
            user_id=user_id,
            action="finding.created",
            entity_type="finding",
            entity_id=finding.id,
            metadata={
                "engagement_id": str(engagement_id),
                "source": "manual",
            },
        )

        await db.refresh(finding)

        asset_identifier = None

        if finding.engagement_asset_id is not None:
            asset = await EngagementRepository.get_asset_by_id(
                db,
                engagement_id=engagement_id,
                asset_id=finding.engagement_asset_id,
            )
            asset_identifier = asset.identifier if asset is not None else None

        return EngagementService.finding_to_list_item(
            finding,
            asset_identifier=asset_identifier,
        )


    @staticmethod
    async def list_retests(
        db: AsyncSession,
        engagement_id: UUID,
        user_id: UUID,
    ) -> RetestListResponse:
        await EngagementService.require_assigned_engagement(
            db,
            engagement_id=engagement_id,
            user_id=user_id,
        )

        retests = await RetestRepository.list_by_engagement(
            db,
            engagement_id=engagement_id,
        )

        return RetestListResponse(
            items = [
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
                )
                for retest in retests
            ]
        )


    @staticmethod
    async def list_activity(
        db: AsyncSession,
        engagement_id: UUID,
        user_id: UUID,
        limit: int = 100,
    ) -> ActivityListResponse:
        await EngagementService.require_assigned_engagement(
            db,
            engagement_id=engagement_id,
            user_id=user_id,
        )

        related_ids = await EngagementRepository.get_related_entity_ids(
            db,
            engagement_id=engagement_id,
        )

        logs = await AuditRepository.list_for_engagement(
            db,
            engagement_id=engagement_id,
            related_entity_ids=related_ids,
            limit=limit,
        )

        users = await EngagementRepository.get_users_by_ids(
            db,
            user_ids = {
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
                        EngagementService.user_summary(users[log.user_id])
                        if log.user_id is not None and log.user_id in users
                        else None
                    ),
                    metadata=log.metadata_,
                    created_at=log.created_at,
                )
                for log in logs
            ]
        )

    @staticmethod
    async def list_messages(
        db: AsyncSession,
        engagement_id: UUID,
        user_id: UUID,
        channel: EngagementMessageChannel,
    ) -> EngagementMessageListResponse:
        await EngagementService.require_message_channel_access(
            db,
            engagement_id=engagement_id,
            user_id=user_id,
            channel=channel,
        )

        comments = await EngagementCommentRepository.list_by_engagement(
            db,
            engagement_id=engagement_id,
            channel=channel,
        )

        user_ids = {
            participant_id
            for comment in comments
            for participant_id in (
                comment.user_id,
                comment.recipient_id,
            )
        }

        users = await EngagementRepository.get_users_by_ids(
            db,
            user_ids=user_ids,
        )

        return EngagementMessageListResponse(
            items=[
                EngagementMessageResponse(
                    id=comment.id,
                    engagement_id=comment.engagement_id,
                    finding_id=comment.finding_id,
                    user=EngagementService.user_summary(users[comment.user_id]),
                    recipient=EngagementService.user_summary(users[comment.recipient_id]),
                    channel=comment.channel,
                    comment=comment.comment,
                    is_read=comment.is_read,
                    created_at=comment.created_at,
                )
                for comment in comments
                if comment.user_id in users
                and comment.recipient_id in users
            ]
        )


    @staticmethod
    async def create_message(
        db: AsyncSession,
        engagement_id: UUID,
        user_id: UUID,
        request: EngagementMessageCreate
    ) -> EngagementMessageResponse:
        engagement = await EngagementService.require_message_channel_access(
            db,
            engagement_id=engagement_id,
            user_id=user_id,
            channel=request.channel,
        )

        comment_text = request.comment.strip()
        if not comment_text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Message cannot be empty.",
            )

        if request.channel == EngagementMessageChannel.CLIENT_SERVICE_DELIVERY:
            if user_id == engagement.requested_by:
                recipient_id = engagement.service_delivery_id
            else:
                recipient_id = engagement.requested_by

        elif request.channel == EngagementMessageChannel.SERVICE_DELIVERY_PENTESTER:
            if user_id == engagement.service_delivery_id:
                recipient_id = engagement.assigned_to
            else:
                recipient_id = engagement.service_delivery_id

        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid message channel.",
            )

        if recipient_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "The other participant has not been assigned to this engagement."
                ),
            )

        if request.finding_id is not None:
            finding = await FindingRepository.get_for_assigned_engagement(
                db,
                finding_id=request.finding_id,
                engagement_id=engagement_id,
            )

            if finding is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="The selected finding does not belong to this engagement.",
                )

        comment = await EngagementCommentRepository.create_comment(
            db,
            engagement_id=engagement_id,
            user_id=user_id,
            recipient_id=recipient_id,
            channel=request.channel,
            comment=comment_text,
            finding_id=request.finding_id,
        )

        await AuditRepository.create_log(
            db,
            user_id=user_id,
            action="engagement.comment_created",
            entity_type="engagement_comment",
            entity_id=comment.id,
            metadata={
                "engagement_id": str(engagement_id),
                "finding_id": (
                    str(request.finding_id)
                    if request.finding_id is not None
                    else None
                ),
                "channel": request.channel.value,
                "recipient_id": str(recipient_id),
            },
        )

        await db.refresh(comment)

        sender = await EngagementRepository.get_user_by_id(
            db,
            user_id=user_id,
        )

        recipient = await EngagementRepository.get_user_by_id(
            db,
            user_id=recipient_id,
        )

        if sender is None or recipient is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Message participant could not be found.",
            )

        return EngagementMessageResponse(
            id=comment.id,
            engagement_id=comment.engagement_id,
            finding_id=comment.finding_id,
            user=EngagementService.user_summary(sender),
            recipient=EngagementService.user_summary(recipient),
            channel=comment.channel,
            comment=comment.comment,
            is_read=comment.is_read,
            created_at=comment.created_at,
        )


    @staticmethod
    async def get_message_conversations(
        db: AsyncSession,
        user_id: UUID,
    ) -> PentesterConversationListResponse:
        rows = await EngagementRepository.get_pentester_conversation_summaries(
            db, 
            pentester_id=user_id,
        )

        items: list[PentesterConversationSummary] = []

        for (
            engagement, 
            service_delivery, 
            latest_comment, 
            sender, 
            message_count, 
            unread_count
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
                PentesterConversationSummary(
                    engagement_id=engagement.id,
                    engagement_title=engagement.title,
                    service_delivery=MessageClientSummary(
                        id=service_delivery.id,
                        full_name=service_delivery.full_name,
                        email=service_delivery.email,
                    ),
                    last_message=last_message,
                    message_count=message_count,
                    unread_count=unread_count,
                )
            )

        return PentesterConversationListResponse(items=items)


    @staticmethod
    async def mark_messages_read(
        db: AsyncSession,
        engagement_id: UUID,
        user_id: UUID,
        channel:EngagementMessageChannel,
    ) -> MarkMessagesReadResponse:
        await EngagementService.require_message_channel_access(
            db,
            engagement_id=engagement_id,
            user_id=user_id,
            channel=channel,
        )
        
        marked_read = await EngagementRepository.mark_messages_read(
            db,
            engagement_id=engagement_id,
            user_id=user_id,
            channel=channel,
        )

        return MarkMessagesReadResponse(marked_read=marked_read)


    @staticmethod
    async def submit_for_review(
        db: AsyncSession,
        engagement_id: UUID,
        user_id: UUID,
    ) -> EngagementStatusResponse:
        engagement = await EngagementRepository.get_by_id(
            db,
            engagement_id=engagement_id,
        )

        if engagement is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Engagement not found.",
            )

        if engagement.assigned_to != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not assigned to this engagement.",
            )

        if engagement.status != EngagementStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only engagements in progress can be submitted for review.",
            )

        engagement = await EngagementRepository.update_status(
            db,
            engagement=engagement,
            new_status=EngagementStatus.REVIEW,
        )

        response_id = engagement.id
        response_status = engagement.status
        response_updated_at = engagement.updated_at

        await AuditRepository.create_log(
            db,
            user_id=user_id,
            action="engagement.submitted_for_review",
            entity_type="engagement",
            entity_id=engagement.id,
            metadata={
                "previous_status": "in_progress",
                "new_status": "review",
            },
        )

        version = 1

        new_report = Report(
            engagement_id=engagement_id, 
            version=version,
            status=ReportStatus.PENDING,
        )
        db.add(new_report)
        await db.commit() 

        render_engagement_report_pdf_task.delay(
            engagement_id=str(engagement_id),
            version=version,
        )

        return EngagementStatusResponse(
            id=response_id,
            status=response_status,
            updated_at=response_updated_at,
        )