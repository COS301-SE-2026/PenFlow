from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import EngagementMessageChannel
from app.models.engagement_comment import EngagementComment


class EngagementCommentRepository:
    @staticmethod
    async def list_by_engagement(
        db: AsyncSession, 
        engagement_id: UUID,
        channel: EngagementMessageChannel,
    ) -> list[EngagementComment]:
        query = select(EngagementComment).where(
            EngagementComment.engagement_id == engagement_id,
            EngagementComment.channel == channel,
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
        recipient_id: UUID,
        channel: EngagementMessageChannel,
        comment: str,
        finding_id: UUID | None = None
    ) -> EngagementComment:
        rec = EngagementComment(
            engagement_id=engagement_id,
            finding_id=finding_id,
            user_id=user_id,
            recipient_id=recipient_id,
            channel=channel,
            comment=comment,
            is_read=True,
        )

        db.add(rec)
        await db.commit()
        await db.refresh(rec)

        return rec