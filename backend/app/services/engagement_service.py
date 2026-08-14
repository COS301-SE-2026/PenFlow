from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import EngagementStatus

from app.models.engagement import Engagement
from app.models.finding import Finding
from app.models.user import User
from app.repositories.engagement_repository import EngagementRepository

from app.schemas.engagement import (
    EngagementAssetResponse,
    EngagementCounts,
    EngagementDetailResponse,
    EngagementListItem,
    EngagementListResponse,
    EngagementOverviewCounts,
    EngagementPagination,
    EngagementSortField,
    PreviousScanSummary,
    SortOrder,
    UserSummary,
)

from app.schemas.finding import FindingListItem

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
            review_status=finding.review_status,
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
            ) 
            for engagement, client_name, asset_count in rows
        ]

        return EngagementListResponse(
            items=items,
            counts = EngagementCounts(
                all=sum(status_counts.values()),
                requested=status_counts.get(EngagementStatus.REQUESTED, 0),
                scoping=status_counts.get(EngagementStatus.SCOPING, 0),
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
        engagement = await EngagementService.require_assigned_engagement(
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
            priority=engagement.priority,
            status=engagement.status,
            scope=engagement.scope,
            estimated_quote=engagement.estimated_quote,
            estimated_duration_days=engagement.estimated_duration_days,
            requested_start_date=engagement.requested_start_date,
            target_date=EngagementRepository.calc_target_date(
                engagement.requested_start_date,
                engagement.estimated_duration_days,
            ),
            started_at=engagement.started_at,
            completed_at=engagement.completed_at,
            created_at=engagement.created_at,
            updated_at=engagement.updated_at,
            client=EngagementService.user_summary(client),
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


   