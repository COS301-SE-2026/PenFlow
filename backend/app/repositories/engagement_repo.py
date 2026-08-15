from typing import Sequence
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.engagement import Engagement
from app.models.audit_log import AuditLog

class EngagementRepository:
    @staticmethod
    async def list_engagements(
        db: AsyncSession, user_id: UUID
    ) -> Sequence[Engagement]:

        query = (
            select(Engagement)
            .where(Engagement.trquested_by == user_id)
            .order_by(desc(Engagement.created_at))
        )

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod 
    async def get_activity_by_engagement_id(
        db: AsyncSession, engagement_id: UUID
    ) -> Sequence[ActivityLog]:

        query = (
            select(AuditLog)
            .where(
                AuditLog.entity_id == engagement_id,
                AuditLog.entity_type == "engagement"
            )
            .order_by(desc(AuditLog.created_at))
        )

        result = await db.execute(query)
        return result.scalars().all()