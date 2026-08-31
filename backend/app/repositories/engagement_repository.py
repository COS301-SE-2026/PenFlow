from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.models.base import EngagementStatus, EngagementType
from app.models.engagement import Engagement
from app.models.engagement_asset import EngagementAsset
from app.models.engagement_comment import EngagementComment
from app.models.finding import Finding
from app.models.finding_retest import FindingRetest
from app.models.scan import Scan
from app.models.user import User
from app.schemas.engagement import (
    EngagementCreateRequest,
    EngagementSortField,
    SortOrder,
)

#Fixed base cost by engagement tier, charged once per engagement
BASE_COST: dict[EngagementType, Decimal] = {
    EngagementType.BLACK_BOX: Decimal("600.00"),
    EngagementType.GREY_BOX: Decimal("800.00"),
    EngagementType.WHITE_BOX: Decimal("1000.00"),
}

# Flat per-asset, per-day rate, same across all tiers
ASSET_DAILY_RATE = Decimal("2.00")

# day calculation 
def calculate_duration_days(start_date: date | None, end_date: date | None) -> int:
    if start_date is None or end_date is None:
        return 0
    return (end_date - start_date).days

#calculate estimate quote
def calculate_estimated_quote(
    engagement_type: EngagementType,
    duration_days: int,
    asset_count: int,
)-> Decimal:
    # the  quote formula still need to confirm
    return BASE_COST[engagement_type] + (ASSET_DAILY_RATE * asset_count * duration_days)

#the engagement is the main ticket
#assets are subsequent rows
class EngagementRepository:
    @staticmethod
    async def create_engagement\
    (
        db: AsyncSession,
        request: EngagementCreateRequest,
        client_user_id: UUID,
    ) -> Engagement:
        objective = request.objective.strip()
        duration_days = calculate_duration_days(request.start_date, request.end_date)
        engagement = Engagement\
        (
            requested_by=client_user_id,
            assigned_to=None,
            engagement_type=request.engagement_type,
            assessment_type=request.assessment_type,
            priority="medium",
            status=EngagementStatus.SCOPING,
            title=objective[:255],
            scope=objective,
            objective=objective,
            estimated_quote=calculate_estimated_quote(
                request.engagement_type, duration_days, len(request.assets)
            ),
            estimated_duration_days=duration_days or None,
            requested_start_date=request.start_date,
            requested_end_date=request.end_date,
            constraints=request.constraints.strip() if request.constraints else None,
            primary_contact=request.primary_contact.strip() if request.primary_contact else None,
        )

        engagement.assets = \
        [
            EngagementAsset\
            (
                identifier=asset.value.strip(),
                asset_type=asset.type.value,
                asset_metadata={},
            )
            for asset in request.assets
        ]

        db.add(engagement)
        await db.commit()
        await db.refresh(engagement)

        return engagement

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
        user_role: str,
        engagement_status: EngagementStatus | None,
        search: str | None,
        sort: EngagementSortField,
        order: SortOrder,
        limit: int,
        offset: int,
    ) -> tuple[list[tuple[Engagement, str, int, str | None]], int]:
        client = aliased(User)
        pentester = aliased(User)

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
                pentester.full_name.label("pentester_name")
            ).join(client, client.id == Engagement.requested_by)
            .outerjoin(
                pentester, pentester.id == Engagement.assigned_to)
                .outerjoin(
                    asset_count_subquery,
                    asset_count_subquery.c.engagement_id == Engagement.id,
            )
        )

        count_query = select(func.count(Engagement.id)).join(client, client.id == Engagement.requested_by)

        if user_role in {"pentester", "admin"}:
            query = query.where(Engagement.assigned_to == user_id)
            count_query = count_query.where(Engagement.assigned_to == user_id)
        else:
            query = query.where(Engagement.requested_by == user_id)
            count_query = count_query.where(Engagement.requested_by == user_id)

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
    async def get_status_counts(db: AsyncSession, user_id: UUID, user_role: str = "client") -> dict[EngagementStatus, int]:
        query = select(Engagement.status, func.count(Engagement.id))

        if user_role in {"pentester", "admin"}:
            query = query.where(Engagement.assigned_to == user_id)
        else:
            query = query.where(Engagement.requested_by == user_id)

        query = query.group_by(Engagement.status)

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
        asset_id:UUID,
        )-> EngagementAsset | None:
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


    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()


    @staticmethod
    async def get_users_by_ids(db: AsyncSession, user_ids: set[UUID]) -> dict[UUID, User]:
        if not user_ids:
            return {}

        query = select(User).where(User.id.in_(user_ids))
        result = await db.execute(query)

        users = list(result.scalars().all())
        return {user.id: user for user in users}


    @staticmethod
    async def get_related_entity_ids(db: AsyncSession, engagement_id: UUID) -> list[UUID]:
        finding_result = await db.execute(select(Finding.id).where(
                Finding.engagement_id == engagement_id
            )
        )

        finding_ids = list(finding_result.scalars().all())

        comment_result = await db.execute(
            select(EngagementComment.id).where(
                EngagementComment.engagement_id == engagement_id
            )
        )

        comment_ids = list(comment_result.scalars().all())

        retest_ids: list[UUID] = []

        if finding_ids:
            retest_result = await db.execute(
                select(FindingRetest.id).where(
                    FindingRetest.finding_id.in_(finding_ids)
                )
            )

            retest_ids = list(retest_result.scalars().all())

        return [*finding_ids, *comment_ids, *retest_ids]


    @staticmethod
    def calc_target_date(
        requested_start_date: date | None,
        estimated_duration_days: int | None,
    ) -> date | None:
        if (
            requested_start_date is None
            or estimated_duration_days is None
        ):
            return None

        return requested_start_date + timedelta(days=estimated_duration_days)
