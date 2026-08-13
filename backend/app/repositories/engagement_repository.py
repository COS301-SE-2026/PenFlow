from datetime import date, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.models.base import EngagementStatus
from app.models.engagement import Engagement
from app.models.engagement_asset import EngagementAsset
from app.models.engagement_comment import EngagementComment
from app.models.finding import Finding
from app.models.finding_retest import FindingRetest
from app.models.scan import Scan
from app.models.user import User
from app.schemas.engagement import EngagementSortField, SortOrder

class EngagementRepository:
    @staticmethod
    async def get_by_id(db: AsyncSession, engagement_id: UUID) -> Engagement | None:
        query = select(Engagement).where(Engagement.id == engagement_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()


    @staticmethod
    async def get_assigned_by_id(
        db: AsyncSession, 
        engagement_id: UUID, 
        user_id: UUID
    ) -> Engagement | None:
        query = select(Engagement).where(
            Engagement.id == engagement_id, 
            Engagement.assigned_to == user_id,
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()


    @staticmethod
    def sort_records(
        query: Select[Any],
        sort: EngagementSortField,
        order: SortOrder,
    ) -> Select[Any]:
        sort_cols: dict[
            EngagementSortField,
            InstrumentedAttribute[Any],
        ] = {
            EngagementSortField.CREATED_AT: Engagement.created_at,
            EngagementSortField.UPDATED_AT: Engagement.updated_at,
            EngagementSortField.STATUS: Engagement.status,
            EngagementSortField.REQUESTED_START_DATE: Engagement.requested_start_date,
        }

        if sort == EngagementSortField.CLIENT:
            return query

        sort_col = sort_cols[sort]

        if order == SortOrder.ASC:
            return query.order_by(sort_col.asc(), Engagement.id.asc())

        return query.order_by(sort_col.desc(), Engagement.id.desc())


    @staticmethod
    async def list_assigned(
        db: AsyncSession,
        *,
        user_id: UUID,
        engagement_status: EngagementStatus | None,
        search: str | None,
        sort: EngagementSortField,
        order: SortOrder,
        limit: int,
        offset: int,
    ) -> tuple[list[tuple[Engagement, str, int]], int]:
        client = aliased(User)

        asset_count_subquery = (
            select(
                EngagementAsset.engagement_id,
                func.count(EngagementAsset.id).label("asset_count"),
            ).group_by(EngagementAsset.engagement_id).subquery()
        )

        query = (
            select(
                Engagement,
                client.full_name.label("client_name"),
                func.coalesce(asset_count_subquery.c.asset_count, 0).label("asset_count"),
            ).join(client, client.id == Engagement.requested_by).outerjoin(
                asset_count_subquery,
                asset_count_subquery.c.engagement_id == Engagement.id,
            ).where(Engagement.assigned_to == user_id)
        )

        count_query = (
            select(func.count(Engagement.id)).join(
                client, client.id == Engagement.requested_by,
            ).where(Engagement.assigned_to == user_id)
        )

        if engagement_status is not None:
            query = query.where(Engagement.status == engagement_status)
            count_query = count_query.where(Engagement.status == engagement_status)

        stripped_search = search.strip() if search else None
        if stripped_search:
            search_filter = or_(
                Engagement.title.ilike(f"%{stripped_search}%"),
                client.full_name.ilike(f"%{stripped_search}%"),
            )

            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if sort == EngagementSortField.CLIENT:
            client_order = (
                client.full_name.asc()
                if order == SortOrder.ASC
                else client.full_name.desc()
            )
            query = query.order_by(client_order, Engagement.id.asc())

        else:
            query = EngagementRepository.sort_records(
                query,
                sort=sort,
                order=order,
            )

        query = query.limit(limit).offset(offset)

        result = await db.execute(query)

        rows = [
            (
                row[0],
                row.client_name or "",
                int(row.asset_count or 0),
            ) for row in result.all()
        ]

        total = int(await db.scalar(count_query) or 0)
        return rows, total


    @staticmethod
    async def get_status_counts(db: AsyncSession, user_id: UUID) -> dict[EngagementStatus, int]:
        query = (
            select(
                Engagement.status, func.count(Engagement.id),
            ).where(Engagement.assigned_to == user_id).group_by(Engagement.status)
        )

        result = await db.execute(query)

        counts = {
            engagement_status: 0
            for engagement_status in EngagementStatus
        }

        for engagement_status, count in result.all():
            counts[engagement_status] = int(count)

        return counts


    @staticmethod
    async def get_assets(db: AsyncSession, engagement_id: UUID) -> list[EngagementAsset]:
        query = (
            select(EngagementAsset).where(
                EngagementAsset.engagement_id == engagement_id
            ).order_by(EngagementAsset.created_at.asc(), EngagementAsset.id.asc())
        )

        result = await db.execute(query)

        return list(result.scalars().all())


    @staticmethod
    async def get_asset_by_id(
        db: AsyncSession,
        engagement_id: UUID,
        asset_id: UUID,
    ) -> EngagementAsset | None:
        query = select(EngagementAsset).where(
            EngagementAsset.id == asset_id,
            EngagementAsset.engagement_id == engagement_id,
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()


    @staticmethod
    async def get_overview_finding_counts(db: AsyncSession, engagement_id: UUID) -> tuple[int, int]:
        manual_query = select(func.count(Finding.id)).where(
            Finding.engagement_id == engagement_id,
            func.lower(Finding.source) == "manual",
        )

        automated_query = select(func.count(Finding.id)).where(
            Finding.engagement_id == engagement_id,
            func.lower(Finding.source) != "manual",
        )

        manual_count = int(await db.scalar(manual_query) or 0)
        automated_count = int(await db.scalar(automated_query) or 0)

        return manual_count, automated_count


    @staticmethod
    async def get_recent_findings(
        db: AsyncSession,
        engagement_id: UUID,
        limit: int = 5,
    ) -> list[tuple[Finding, str | None]]:
        query = (
            select(Finding, EngagementAsset.identifier.label("asset_identifier"))
            .outerjoin(EngagementAsset, EngagementAsset.id == Finding.engagement_asset_id)
            .where(Finding.engagement_id == engagement_id)
            .order_by(Finding.created_at.desc(), Finding.id.desc())
            .limit(limit)
        )

        result = await db.execute(query)

        return [
            (
                row[0],
                row.asset_identifier,
            ) for row in result.all()
        ]


    @staticmethod
    async def get_previous_scan_summary(
        db: AsyncSession,
        engagement_id: UUID,
    ) -> tuple[UUID, str, datetime | None, int] | None:
        linked_scan_ids = (
            select(Finding.scan_id).where(
                Finding.engagement_id == engagement_id,
                Finding.scan_id.is_not(None),
            ).distinct().subquery()
        )

        scan_query = (
            select(Scan.id, Scan.domain, Scan.completed_at).where(
                Scan.id.in_(select(linked_scan_ids.c.scan_id))
            ).order_by(
                Scan.completed_at.desc().nullslast(),
                Scan.created_at.desc(),
            ).limit(1)
        )

        result = await db.execute(scan_query)
        row = result.one_or_none()

        if row is None:
            return None

        scan_id = cast(UUID, row[0])
        domain = cast(str, row[1])
        completed_at = cast(datetime | None, row[2])

        finding_count_query = select(func.count(Finding.id)).where(
            Finding.engagement_id == engagement_id,
            Finding.scan_id == scan_id,
        )

        finding_count = int(await db.scalar(finding_count_query) or 0)

        return (scan_id, domain, completed_at, finding_count)
