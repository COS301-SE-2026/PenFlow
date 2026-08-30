from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import Select, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.models.audit_log import AuditLog
from app.models.base import EngagementStatus
from app.models.engagement import Engagement
from app.schemas.engagement import EngagementSortField, SortOrder


class EngagementRepository:

    @staticmethod
    async def list_engagements(
        db: AsyncSession, user_id: UUID
    ) -> Sequence[Engagement]:

        query = (
            select(Engagement)
            .where(Engagement.requested_by == user_id)
            .order_by(desc(Engagement.created_at))
        )

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod 
    async def get_activity_by_engagement_id(
        db: AsyncSession, engagement_id: UUID
    ) -> Sequence[AuditLog]:

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
    def sort_records(
        query: Select[Any], sort: EngagementSortField, order: SortOrder
    ) -> Select[Any]:
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

    @staticmethod
    async def list_admin_engagements(
        db: AsyncSession,
        search: str | None,
        status: EngagementStatus | None,
        pentester_id: UUID | None,
        assignment_status: str | None,
        sort: EngagementSortField,
        order: SortOrder,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[Engagement], int]:

        query = select(Engagement)
        count_query = select(func.count(Engagement.id))

        stripped_search = search.strip() if search else None
        if stripped_search:
            search_filter = Engagement.title.ilike(f"%{stripped_search}%")
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if status is not None:
            query = query.where(Engagement.status == status)
            count_query = count_query.where(Engagement.status == status)

        if pentester_id is not None:
            query = query.where(Engagement.assigned_to == pentester_id)
            count_query = count_query.where(Engagement.assigned_to == pentester_id)

        if assignment_status == "assigned":
            query = query.where(Engagement.assigned_to.isnot(None))
            count_query = count_query.where(Engagement.assigned_to.isnot(None))
        elif assignment_status == "unassigned":
            query = query.where(Engagement.assigned_to.is_(None))
            count_query = count_query.where(Engagement.assigned_to.is_(None))

        query = EngagementRepository.sort_records(query,sort=sort, order=order)
        query = query.limit(limit).offset(offset)

        result = await db.execute(query)
        engagements = result.scalars().all

        total = int(await db.scalar(count_query) or 0)

        return engagements, total

    @staticmethod
    async def get_status_counts(db: AsyncSession) -> dict[EngagementStatus, int]:
        query = select(Engagement.status, func.count(Engagement.id)).group_by(Engagement.status)
        result = await db.execute(query)

        counts = {status: 0 for status in EngagementStatus}
        for status, count in result.all():
            counts[status] = int(count)

        return counts