import logging
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import NotificationType
from app.models.notification import Notification
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository
from app.schemas.engagement import EngagementPagination
from app.schemas.notification import (
    MarkNotificationsReadResponse,
    NotificationListResponse,
    NotificationResponse,
)
from app.tasks.email_tasks import send_email_task

EMAIL_NOTIFICATION_TYPES = {
    NotificationType.ENGAGEMENT_CLAIMED,
    NotificationType.ENGAGEMENT_ASSIGNED,
    NotificationType.ENGAGEMENT_SCHEDULED,
    NotificationType.ENGAGEMENT_REASSIGNED,
    NotificationType.ENGAGEMENT_RESCHEDULED,
    NotificationType.ENGAGEMENT_REVIEW_REQUIRED,
    NotificationType.ENGAGEMENT_REVIEW_RETURNED,
    NotificationType.ENGAGEMENT_STARTED,
    NotificationType.ENGAGEMENT_COMPLETED,
    NotificationType.ENGAGEMENT_CANCELLED,
}

logger = logging.getLogger(__name__)

class NotificationService:

    @staticmethod
    def notification_response(
        notification: Notification,
    ) -> NotificationResponse:
        return NotificationResponse.model_validate(notification)


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
        return await NotificationRepository.create_notification(
            db,
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            engagement_id=engagement_id,
            metadata=metadata,
        )


    @staticmethod
    async def list_notifications(
        db: AsyncSession,
        *,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> NotificationListResponse:
        notifications, total = await NotificationRepository.list_for_user(
            db,
            user_id=user_id,
            unread_only=unread_only,
            limit=limit,
            offset=offset,
        )

        unread_count = await NotificationRepository.count_unread(
            db,
            user_id=user_id,
        )

        items = [
            NotificationService.notification_response(notification)
            for notification in notifications
        ]

        return NotificationListResponse(
            items=items,
            unread_count=unread_count,
            pagination=EngagementPagination(
                total=total,
                limit=limit,
                offset=offset,
                has_more=offset + len(items) < total,
            ),
        )


    @staticmethod
    async def mark_notification_read(
        db: AsyncSession,
        notification_id: UUID,
        user_id: UUID,
    ) -> NotificationResponse:
        notification = await NotificationRepository.mark_read(
            db,
            notification_id=notification_id,
            user_id=user_id,
        )

        if notification is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found.",
            )

        return NotificationService.notification_response(notification)


    @staticmethod
    async def mark_all_notifications_read(
        db: AsyncSession,
        user_id: UUID,
    ) -> MarkNotificationsReadResponse:
        marked_read = await NotificationRepository.mark_all_read(
            db,
            user_id=user_id,
        )

        return MarkNotificationsReadResponse(marked_read=marked_read)


    @staticmethod
    async def notify(
        db: AsyncSession,
        *,
        recipient_id: UUID | None,
        actor_id: UUID | None,
        notification_type: NotificationType,
        title: str,
        message: str,
        engagement_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Notification | None:
        if recipient_id is None:
            return None

        if actor_id is not None and recipient_id == actor_id:
            return None

        notification = await NotificationRepository.create_notification(
            db,
            user_id=recipient_id,
            notification_type=notification_type,
            title=title,
            message=message,
            engagement_id=engagement_id,
            metadata=metadata or {},
        )

        if notification_type in EMAIL_NOTIFICATION_TYPES:
            recipient = await db.get(User, recipient_id)

            if recipient is not None and recipient.email:
                try:
                    send_email_task.apply_async(
                        kwargs={
                            "to_email": recipient.email,
                            "subject": title,
                            "text_body": message,
                        },
                        queue="email",
                    )
                except Exception:
                    logger.exception(
                        "Failed to queue notification email for notification %s",
                        notification.id
                    )

        return notification


    
    