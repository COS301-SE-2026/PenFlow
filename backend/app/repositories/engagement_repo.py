from typing import Sequence
from uuid import UUID

from sqlalchemy import desc, func, Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalcemy.orm.attributes import InstrumentedAttribute

from app.models.base import EngagementStatus
from app.models.engagement import Engagement
from app.models.audit_log import AuditLog
from app.schemas.engagement import EngagementSortField, SortOrder

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

    @staticmethod
    def sort_records(query: Select[Any], sort: EngagementSortField, order: SortOrder) -> Select[Any]:
        sort_cols: dict[EngagementSortField, InstrumentedAttribute[Any]] = {
            EngagementSortField.CREATED_AT: Engagement.created_at,
            EngagementSortField.UPDATED_AT: Engagement.updated_at,
            EngagementSortField.STATUS: Engagement.status,
            EngagementSortField.REQUESTED_START_DATE: Engagement.requested_start_date,
        }

        sort_col = sort_cols.get(sort, Engagement.created_at)

        if order == SortOrder.ASC:
            return query.order_by(sort_col.asc(), Engagement.id.asc())
        return query.order_by(sort_col.desc(), Engagement.id.desc())