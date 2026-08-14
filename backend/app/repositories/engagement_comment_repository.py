from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.engagement_comment import EngagementComment


class EngagementCommentRepository:
    @staticmethod
    async def list_by_engagement(
        db: AsyncSession, 
        engagement_id: UUID
    ) -> list[EngagementComment]:
        query = select(EngagementComment).where(
            EngagementComment.engagement_id == engagement_id
        ).order_by(
            EngagementComment.created_at.asc(), 
            EngagementComment.id.asc(),
        )

        result = await db.execute(query)
        return list(result.scalars().all())


    @staticmethod
    async def create_comment(
        db: AsyncSession,
        *,
        engagement_id: UUID,
        user_id: UUID,
        comment: str,
        finding_id: UUID | None = None
    ) -> EngagementComment:
        rec = EngagementComment(
            engagement_id=engagement_id,
            finding_id=finding_id,
            user_id=user_id,
            comment=comment,
        )

        db.add(rec)
        await db.commit()
        await db.refresh(rec)

        return rec