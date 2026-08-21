from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import EngagementStatus
from app.models.engagement import Engagement
from app.models.user import User


class AdminRepository:
    @staticmethod
    async def list_users\
    (
        db: AsyncSession,
        *,
        search: str | None,
        role: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[tuple[User, int]], int]:
        #list of statuses for engagements so far
        active_statuses = \
        [
            EngagementStatus.REQUESTED,
            EngagementStatus.SCOPING,
            EngagementStatus.IN_PROGRESS,
            EngagementStatus.REVIEW,
        ]

        filters = []

        #search
        if search:
            filters.append\
            (
                or_\
                (
                    User.full_name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%"),
                )
            )

        #role
        if role:
            filters.append(User.role == role)

        engagement_join_condition = or_\
        (
            and_\
            (
                User.role == "pentester",
                Engagement.assigned_to == User.id,
            ),
            and_\
            (
                User.role == "client",
                Engagement.requested_by == User.id,
            ),
        )

        query = \
        (
            select(
                User,
                func.count(Engagement.id).label("active_engagements"),
            )
            .outerjoin(
                Engagement,
                and_(
                    engagement_join_condition,
                    Engagement.status.in_(active_statuses),
                ),
            )
            .where(*filters)
            .group_by(User.id)
            .order_by(User.created_at.desc(), User.id.asc())
            .limit(limit)
            .offset(offset)
        )

        count_query = select(func.count(User.id)).where(*filters)

        result = await db.execute(query)

        rows = \
        [
            (
                row[0],
                int(row.active_engagements or 0),
            )
            for row in result.all()
        ]

        total = int(await db.scalar(count_query) or 0)

        return rows, total