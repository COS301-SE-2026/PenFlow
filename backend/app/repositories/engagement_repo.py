from typing import Sequence
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.engagement import Engagement
from app.models.activity_event import ActivityEvent

class EngagementRepository:
    @staticmethod
    async def list_engagements(
        db: AsyncSession, user_id: UUID
    ) -> Sequence[Engagement]:

        query = (
            select(Engagement)
            .where(Engagement.user_id == user_id)
            .order_by(desc(Engagement.created_at))
        )

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod 
    async def get_activity_by_engagement_id(
        db: AsyncSession, engagement_id: UUID, user_id: UUID 
    ) -> Sequence[ActivityEvent]:

        query = (
            select(ActivityEvent)
            .join(Engagement, ActivityEvent.engagement_id == Engagement.id)
            .where(
                ActivityEvent.engagement_id == engagement_id,
                Engagement.user_id == user_id 
            )
            .order_by(desc(ActivityEvent.timestamp))
        )

        result = await db.execute(query)
        return result.scalars().all()