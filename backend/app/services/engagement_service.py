from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import EngagementStatus

from app.models.engagement import Engagement
from app.models.finding import Finding
from app.models.user import User
from app.repositories.engagement_repository import EngagementRepository
from app.schemas.engagement import (
    EngagementCounts,
    EngagementListItem,
    EngagementListResponse,
    EngagementPagination,
    EngagementSortField,
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