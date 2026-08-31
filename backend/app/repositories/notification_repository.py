from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import NotificationType
from app.models.notification import Notification


class NotificationRepository:

    @staticmethod
    async def create_notification(
        db: AsyncSession,
        *,
        user_id: UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        engagement_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            type=notification_type.value,
            title=title,
            message=message,
            engagement_id=engagement_id,
            metadata_=metadata or {},
        )

        db.add(notification)
        await db.commit()
        await db.refresh(notification)

        return notification


    @staticmethod
    async def list_for_user(
        db: AsyncSession,
        *,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Notification], int]:
        filters = [
            Notification.user_id == user_id,
        ]

        if unread_only:
            filters.append(Notification.is_read.is_(False))


        count_stmt = (
            select(func.count()).select_from(Notification).where(
                *filters
            )
        )

        total = int((await db.execute(count_stmt)).scalar_one())

        stmt = (
            select(Notification).where(*filters).order_by(
                Notification.created_at.desc(),
                Notification.id.desc(),
            ).limit(limit).offset(offset)
        )

        result = await db.execute(stmt)
        return list(result.scalars().all()), total


    @staticmethod
    async def count_unread(
        db: AsyncSession,
        user_id: UUID,
    ) -> int:
        stmt = (
            select(func.count()).select_from(Notification).where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )

        result = await db.execute(stmt)
        return int(result.scalar_one())


    @staticmethod
    async def get_by_id_for_user(
        db: AsyncSession,
        notification_id: UUID,
        user_id: UUID,
    ) -> Notification | None:
        stmt = (
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )

        result = await db.execute(stmt)
        return result.scalar_one_or_none()


    @staticmethod
    async def mark_read(
        db: AsyncSession,
        notification_id: UUID,
        user_id: UUID,
    ) -> Notification | None:
        notification = await NotificationRepository.get_by_id_for_user(
            db,
            notification_id=notification_id,
            user_id=user_id,
        )

        if notification is None:
            return None

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)

            await db.commit()
            await db.refresh(notification)

        return notification


    @staticmethod
    async def mark_all_read(
        db: AsyncSession,
        user_id: UUID,
    ) -> int:
        stmt = (
            update(Notification).where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            ).values(
                is_read=True,
                read_at=datetime.now(timezone.utc),
            )
        )

        result = await db.execute(stmt)
        await db.commit()

        return result.rowcount or 0