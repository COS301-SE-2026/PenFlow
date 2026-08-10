from typing import Sequence
from uuid import UUID 

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_event import ActivityEvent
from app.models.engagement import Engagement
from app.repositories.engagement_repo import EngagementRepository 

async def get_all_engagements(
        db: AsyncSession, user_id: UUID
) -> Sequence[Engagement]:
    """
    Fetch all engagement.
    """
    return await EngagementRepository.list_engagements(db=db, user_id=user_id)

async def get_engagement_activity(
    db: AsyncSession, engagement_id: UUID, user_id: UUID
) -> Sequence[ActivityEvent]:
    """
    Fetch chronological event log.
    """
    return await EngagementRepository.get_activity_by_engagement_id(
        db=db, engagement_id=engagement_id, user_id=user_id 
    )