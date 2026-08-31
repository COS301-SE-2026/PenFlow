from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Select, case, func, or_, select, update
from sqlalchemy.engine import CursorResult, Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.models.base import (
    AssessmentType,
    EngagementMessageChannel,
    EngagementStatus,
    EngagementType,
    RetestStatus,
    Severity,
)
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
    async def create_engagement(
        db: AsyncSession,
        request: EngagementCreateRequest,
        client_user_id: UUID,
    ) -> Engagement:
        objective = request.objective.strip()
        duration_days = calculate_duration_days(request.start_date, request.end_date)
        engagement = Engagement(
            requested_by=client_user_id,
            service_delivery_id=None,
            assigned_to=None,
            engagement_type=request.engagement_type,
            assessment_type=request.assessment_type,
            priority="medium",
            status=EngagementStatus.REQUESTED,
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


    @staticmethod
    async def get_pentester_conversation_summaries(
        db: AsyncSession,
        pentester_id: UUID,
    ) -> list[tuple[Any, ...]]:
        service_delivery = aliased(User)
        sender = aliased(User)

        message_count_subquery = (
            select(
                EngagementComment.engagement_id,
                func.count(EngagementComment.id).label(
                    "message_count"
                ),
            )
            .where(
                EngagementComment.channel == EngagementMessageChannel.SERVICE_DELIVERY_PENTESTER
            )
            .group_by(EngagementComment.engagement_id)
            .subquery()
        )

        latest_message_time_subquery = (
            select(
                EngagementComment.engagement_id,
                func.max(EngagementComment.created_at).label(
                    "latest_created_at"
                )
            ).where(
                EngagementComment.channel == EngagementMessageChannel.SERVICE_DELIVERY_PENTESTER
            )
            .group_by(EngagementComment.engagement_id)
            .subquery()
        )

        unread_count_subquery = (
            select(
                EngagementComment.engagement_id,
                func.count(EngagementComment.id).label(
                    "unread_count"
                ),
            ).where(
                EngagementComment.channel == EngagementMessageChannel.SERVICE_DELIVERY_PENTESTER,
                EngagementComment.recipient_id == pentester_id,
                EngagementComment.is_read.is_(False),
            ).group_by(
                EngagementComment.engagement_id
            ).subquery()
        )

        latest_comment = aliased(EngagementComment)

        stmt = (
            select(Engagement, service_delivery, latest_comment, sender, 
                   func.coalesce(
                       message_count_subquery.c.message_count,
                       0,
                   ).label("message_count"),
                   func.coalesce(
                       unread_count_subquery.c.unread_count,
                       0,
                   ).label("unread_count"),
            ).join(
                service_delivery,
                service_delivery.id == Engagement.service_delivery_id,
            ).outerjoin(
                message_count_subquery,
                message_count_subquery.c.engagement_id == Engagement.id,
            ).outerjoin(
                latest_message_time_subquery,
                latest_message_time_subquery.c.engagement_id == Engagement.id,
            ).outerjoin(
                unread_count_subquery,
                unread_count_subquery.c.engagement_id == Engagement.id,
            ).outerjoin(
                latest_comment,
                (latest_comment.engagement_id == Engagement.id) & (
                latest_comment.created_at == latest_message_time_subquery.c.latest_created_at) & (
                    latest_comment.channel == EngagementMessageChannel.SERVICE_DELIVERY_PENTESTER
                ),
            ).outerjoin(
                sender,
                sender.id == latest_comment.user_id,
            ).where(
                Engagement.assigned_to == pentester_id,
                message_count_subquery.c.message_count.is_not(None),
            ).order_by(
                latest_message_time_subquery.c.latest_created_at.desc().nullslast(),
                Engagement.updated_at.desc(),
            )
        )

        result = await db.execute(stmt)
        return list(result.all())


    @staticmethod
    async def mark_messages_read(
        db: AsyncSession,
        engagement_id: UUID,
        user_id: UUID,
        channel: EngagementMessageChannel,
    ) -> int:
        stmt = (
            update(EngagementComment).where(
                EngagementComment.engagement_id == engagement_id,
                EngagementComment.recipient_id == user_id,
                EngagementComment.channel == channel,
                EngagementComment.is_read.is_(False),
            ).values(is_read=True)
        )

        result = cast(CursorResult[Any], await db.execute(stmt))
        await db.commit()

        return max(result.rowcount, 0)


    @staticmethod
    async def update_status(
        db: AsyncSession,
        engagement: Engagement,
        new_status: EngagementStatus,
    ) -> Engagement:
        engagement.status = new_status

        await db.commit()
        await db.refresh(engagement)

        return engagement


    @staticmethod
    async def list_for_service_delivery(
        db: AsyncSession,
        *,
        engagement_status: EngagementStatus | None,
        assessment_type: AssessmentType | None,
        search: str | None,
        pentester_id: UUID | None,
        assigned: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[list[tuple[Engagement, User, User | None, User | None]], int]:

        client = aliased(User)
        service_delivery = aliased(User)
        pentester = aliased(User)

        query = (
            select(
                Engagement,
                client,
                service_delivery,
                pentester,
            ).join(
                client,
                client.id == Engagement.requested_by,
            ).outerjoin(
                service_delivery,
                service_delivery.id == Engagement.service_delivery_id,
            ).outerjoin(
                pentester,
                pentester.id == Engagement.assigned_to,
            )
        )

        count_query = select(func.count(Engagement.id))

        if engagement_status is not None:
            query = query.where(
                Engagement.status == engagement_status
            )
            count_query = count_query.where(
                Engagement.status == engagement_status
            )

        if assessment_type is not None:
            query = query.where(
                Engagement.assessment_type == assessment_type
            )
            count_query = count_query.where(
                Engagement.assessment_type == assessment_type
            )

        if pentester_id is not None:
            query = query.where(
                Engagement.assigned_to == pentester_id
            )
            count_query = count_query.where(
                Engagement.assigned_to == pentester_id
            )

        if assigned is True:
            query = query.where(
                Engagement.assigned_to.is_not(None)
            )
            count_query = count_query.where(
                Engagement.assigned_to.is_not(None)
            )

        elif assigned is False:
            query = query.where(
                Engagement.assigned_to.is_(None)
            )
            count_query = count_query.where(
                Engagement.assigned_to.is_(None)
            )

        stripped_search = search.strip() if search else None

        if stripped_search:
            search_filter = or_(
                Engagement.title.ilike(f"%{stripped_search}%"),
                client.full_name.ilike(f"%{stripped_search}%"),
                client.email.ilike(f"%{stripped_search}%"),
            )

            query = query.where(search_filter)

            count_query = count_query.join(
                client,
                client.id == Engagement.requested_by,
            ).where(search_filter)

        query = query.order_by(
            Engagement.updated_at.desc(),
            Engagement.id.desc(),
        ).limit(limit).offset(offset)

        result = await db.execute(query)
        rows = [
            (
                row[0],
                row[1],
                row[2],
                row[3],
            )
            for row in result.all()
        ]

        total = int(await db.scalar(count_query) or 0)

        return rows, total


    @staticmethod
    async def get_service_delivery_finding_summary(
        db: AsyncSession,
        engagement_id: UUID,
    ) -> tuple[int, int, int, int, int, int]:
        query = (
            select(
                Finding.severity,
                func.count(Finding.id),
            ).where(
                Finding.engagement_id == engagement_id,
            ).group_by(Finding.severity)
        )

        result = await db.execute(query)

        counts = {
            severity: 0
            for severity in Severity
        }

        total = 0

        for severity, count in result.all():
            numeric_count = int(count)
            counts[severity] = numeric_count
            total += numeric_count

        return (
            total,
            counts[Severity.CRITICAL],
            counts[Severity.HIGH],
            counts[Severity.MEDIUM],
            counts[Severity.LOW],
            0,
        )


    @staticmethod
    async def get_service_delivery_retest_summary(
        db: AsyncSession,
        engagement_id: UUID,
    ) -> tuple[int, int, int, int, int]:
        query = (
            select(
                FindingRetest.status,
                func.count(FindingRetest.id),
            ).join(
                Finding,
                Finding.id == FindingRetest.finding_id,
            ).where(
                Finding.engagement_id == engagement_id,
            ).group_by(FindingRetest.status)
        )

        result = await db.execute(query)

        counts = {
            retest_status: 0
            for retest_status in RetestStatus
        }

        total = 0

        for retest_status, count in result.all():
            numeric_count = int(count)
            counts[retest_status] = numeric_count
            total+=numeric_count

        return (
            total,
            counts[RetestStatus.REQUESTED],
            counts[RetestStatus.IN_PROGRESS],
            counts[RetestStatus.RESOLVED],
            counts[RetestStatus.STILL_VULNERABLE],
        )


    @staticmethod
    async def claim(
        db: AsyncSession,
        engagement_id: UUID,
        service_delivery_id: UUID,
    ) -> Engagement | None:
        stmt = (
            update(Engagement).where(
                Engagement.id == engagement_id,
                Engagement.status == EngagementStatus.REQUESTED,
                Engagement.service_delivery_id.is_(None),
            ).values(
                service_delivery_id=service_delivery_id,
                status=EngagementStatus.SCOPING,
            ).returning(Engagement.id)
        )

        result = await db.execute(stmt)
        claimed_id = result.scalar_one_or_none()

        if claimed_id is None:
            await db.rollback()
            return None

        await db.commit()

        return await EngagementRepository.get_by_id(
            db,
            engagement_id=claimed_id,
        )


    @staticmethod
    async def update_scoping(
        db: AsyncSession,
        *,
        engagement: Engagement,
        assessment_type: AssessmentType | None = None,
        scope: str | None = None,
        objective: str | None = None,
        constraints: str | None = None,
        final_quote: Decimal | None = None,
        estimated_duration_days: int | None = None,
    ) -> Engagement:
        if assessment_type is not None:
            engagement.assessment_type = assessment_type

        if scope is not None:
            engagement.scope = scope

        if objective is not None:
            engagement.objective = objective

        if constraints is not None:
            engagement.constraints = constraints

        if final_quote is not None:
            engagement.final_quote = final_quote

        if estimated_duration_days is not None:
            engagement.estimated_duration_days = estimated_duration_days

        await db.commit()
        await db.refresh(engagement)

        return engagement


    @staticmethod
    async def update_fields(
        db: AsyncSession,
        engagement: Engagement,
        changes: dict[str, Any],
    ) -> Engagement:

        for field, value in changes.items():
            setattr(engagement, field, value)

        await db.commit()
        await db.refresh(engagement)

        return engagement


    @staticmethod
    async def has_schedule_conflict(
        db: AsyncSession,
        *,
        pentester_id: UUID,
        scheduled_start_date: date,
        scheduled_end_date: date,
        exclude_engagement_id: UUID | None = None,
    ) -> bool:
        stmt = select(func.count(Engagement.id)).where(
            Engagement.assigned_to == pentester_id,
            Engagement.status.in_(
                [
                    EngagementStatus.SCHEDULED,
                    EngagementStatus.IN_PROGRESS,
                ]
            ),
            Engagement.scheduled_start_date.is_not(None),
            Engagement.scheduled_end_date.is_not(None),
            Engagement.scheduled_start_date <= scheduled_end_date,
            Engagement.scheduled_end_date >= scheduled_start_date,
        )

        if exclude_engagement_id is not None:
            stmt = stmt.where(
                Engagement.id != exclude_engagement_id,
            )

        count = int(await db.scalar(stmt) or 0)

        return count > 0


    @staticmethod
    async def get_service_delivery_dashboard_counts(
        db: AsyncSession,
    ) -> dict[EngagementStatus, int]:
        stmt = (
            select(
                Engagement.status,
                func.count(Engagement.id),
            ).group_by(
                Engagement.status
            )
        )

        result = await db.execute(stmt)

        counts = {
            engagement_status: 0
            for engagement_status in EngagementStatus
        }

        for engagement_status, count in result.all():
            counts[engagement_status] = int(count)

        return counts


    @staticmethod
    async def list_for_service_delivery_dashboard(
        db: AsyncSession,
        engagement_status: EngagementStatus,
        unclaimed_only: bool = False,
        limit: int = 5,
    ) -> list[tuple[Engagement, User, User | None, User | None]]:

        client=  aliased(User)
        service_delivery = aliased(User)
        pentester = aliased(User)

        stmt = (
            select(
                Engagement,
                client,
                service_delivery,
                pentester,
            ).join(
                client,
                client.id == Engagement.requested_by,
            ).outerjoin(
                service_delivery,
                service_delivery.id == Engagement.service_delivery_id,
            ).outerjoin(
                pentester,
                pentester.id == Engagement.assigned_to,
            ).where(
                Engagement.status == engagement_status,
            )
        )

        if unclaimed_only:
            stmt = stmt.where(
                Engagement.service_delivery_id.is_(None),
            )

        if engagement_status == EngagementStatus.SCHEDULED:
            stmt = (
                stmt.where(
                    Engagement.scheduled_start_date >= date.today(),
                ).order_by(
                    Engagement.scheduled_start_date.asc(),
                    Engagement.id.asc(),
                )
            )

        else:
            stmt = stmt.order_by(
                Engagement.updated_at.desc(),
                Engagement.id.desc(),
            )

        stmt = stmt.limit(limit)

        result = await db.execute(stmt)

        return [
            (
                row[0],
                row[1],
                row[2],
                row[3],
            ) for row in result.all()
        ]


    @staticmethod
    async def get_service_delivery_conversation_summaries(
        db: AsyncSession,
        service_delivery_id: UUID,
    ) -> list[Row[Any]]:

        participant = aliased(User)
        sender = aliased(User)
        latest_comment = aliased(EngagementComment)

        message_count_subquery = (
            select(
                EngagementComment.engagement_id,
                EngagementComment.channel,
                func.count(EngagementComment.id).label(
                    "message_count"
                ),
            ).where(
                EngagementComment.channel.in_(
                    [
                        EngagementMessageChannel.CLIENT_SERVICE_DELIVERY,
                        EngagementMessageChannel.SERVICE_DELIVERY_PENTESTER,
                    ]
                )
            ).group_by(
                EngagementComment.engagement_id,
                EngagementComment.channel,
            ).subquery()
        )

        latest_message_time_subquery = (
            select(
                EngagementComment.engagement_id,
                EngagementComment.channel,
                func.max(
                    EngagementComment.created_at,
                ).label("latest_created_at"),
            ).where(
                EngagementComment.channel.in_(
                    [
                        EngagementMessageChannel.CLIENT_SERVICE_DELIVERY,
                        EngagementMessageChannel.SERVICE_DELIVERY_PENTESTER,
                    ]
                )
            ).group_by(
                EngagementComment.engagement_id,
                EngagementComment.channel,
            ).subquery()
        )

        unread_count_subquery = (
            select(
                EngagementComment.engagement_id,
                EngagementComment.channel,
                func.count(
                    EngagementComment.id
                ).label("unread_count")
            ).where(
                EngagementComment.recipient_id == service_delivery_id,
                EngagementComment.is_read.is_(False),
                EngagementComment.channel.in_(
                    [
                        EngagementMessageChannel.CLIENT_SERVICE_DELIVERY,
                        EngagementMessageChannel.SERVICE_DELIVERY_PENTESTER,
                    ]
                )
            ).group_by(
                EngagementComment.engagement_id,
                EngagementComment.channel
            ).subquery()
        )

        stmt = (
            select(
                Engagement,
                message_count_subquery.c.channel,
                participant,
                latest_comment,
                sender,
                func.coalesce(
                    message_count_subquery.c.message_count,
                    0,
                ).label("message_count"),
                func.coalesce(
                    unread_count_subquery.c.unread_count,
                    0,
                ).label("unread_count"),
            ).join(
                message_count_subquery,
                message_count_subquery.c.engagement_id == Engagement.id
            ).join(
                latest_message_time_subquery,
                (latest_message_time_subquery.c.engagement_id == Engagement.id)
                & (latest_message_time_subquery.c.channel == message_count_subquery.c.channel),
            ).outerjoin(
                unread_count_subquery,
                (unread_count_subquery.c.engagement_id == Engagement.id)
                & (unread_count_subquery.c.channel
                    == message_count_subquery.c.channel
                    ),
            ).outerjoin(
                latest_comment,
                (latest_comment.engagement_id == Engagement.id)
                & (latest_comment.channel == message_count_subquery.c.channel)
                & (latest_comment.created_at == latest_message_time_subquery.c.latest_created_at),
            ).outerjoin(
                sender,
                sender.id == latest_comment.user_id,
            ).join(
                participant,
                participant.id
                == case(
                    (
                        message_count_subquery.c.channel
                        == EngagementMessageChannel.CLIENT_SERVICE_DELIVERY,
                        Engagement.requested_by,
                    ),
                    else_=Engagement.assigned_to,
                ),
            ).where(
                Engagement.service_delivery_id == service_delivery_id,
            ).order_by(
                latest_message_time_subquery.c.latest_created_at.desc()
                .nullslast(),
                Engagement.updated_at.desc(),
            )
        )

        result = await db.execute(stmt)
        return list(result.all())


    @staticmethod
    async def get_service_delivery_users(
        db: AsyncSession,
    ) -> list[User]:
        stmt = (
            select(User).where(
                User.role == "service_delivery",
            ).order_by(
                User.created_at.asc(),
            )
        )

        result = await db.execute(stmt)
        return list(result.scalars().all())