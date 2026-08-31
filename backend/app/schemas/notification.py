from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import NotificationType
from app.schemas.engagement import EngagementPagination


class NotificationResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    id: UUID
    type: NotificationType
    title: str
    message: str
    is_read: bool
    read_at: datetime | None
    engagement_id: UUID | None
    metadata: dict[str, Any] = Field(
        validation_alias="metadata_",
    )


    created_at: datetime

class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    unread_count: int
    pagination: EngagementPagination

class MarkNotificationsReadResponse(BaseModel):
    marked_read: int