from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.db import get_db
from app.models.user import User
from app.schemas.notification import (
    MarkNotificationsReadResponse,
    NotificationListResponse,
    NotificationResponse,
)
from app.services.notification_service import NotificationService
from app.api.middleware.auth import require_user

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)

@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List current user notifications",
)
async def list_notifications(
    unread_only: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
) -> NotificationListResponse:
    return await NotificationService.list_notifications(
        db,
        user_id=user.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark notification as read",
)
async def mark_notification_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
) -> NotificationResponse:
    return await NotificationService.mark_notification_read(
        db,
        notification_id=notification_id,
        user_id=user.id,
    )


@router.patch(
    "/read-all",
    response_model=MarkNotificationsReadResponse,
    summary="Mark all notifications as read",
)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
) -> MarkNotificationsReadResponse:
    return await NotificationService.mark_all_notifications_read(
        db,
        user_id=user.id,
    )