from typing import Sequence
from uuid import UUID 

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.engagement import Engagement
from app.repositories.engagement_repo import EngagementRepository 
from app.schemas.engagement import EngagementSortField, SortOrder

async def get_all_engagements(
        db: AsyncSession, user_id: UUID
) -> Sequence[Engagement]:
    """
    Fetch all engagement.
    """
    return await EngagementRepository.list_engagements(db=db, user_id=user_id)

async def get_engagement_activity(
    db: AsyncSession, engagement_id: UUID
) -> Sequence[AuditLog]:
    """
    Fetch chronological event log.
    """
    return await EngagementRepository.get_activity_by_engagement_id(
        db=db, engagement_id=engagement_id
    )

async def get_admin_engagements_paginated(
        db: AsyncSession,
        search: str | None,
        status: str | None,
        pentester_id: UUID | None,
        assignment_status: str | None,
        sort: EngagementSortField,
        order: SortOrder,
        limit: int,
        offset: int,
) -> tuple[Sequence[Engagement], int, dict]:

    engagements, total = await EngagementRepository.list_admin_engagement(
        db=db,
        search=search,
        status=status,
        pentester_id=pentester_id,
        assignment_status=assignment_status,
        sort=sort,
        order=order,
        limit=limit,
        offset=offset,
    )

    counts = await EngagementRepository.get_status_counts(db)

    return engagements, total, counts