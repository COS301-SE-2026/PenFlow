from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.models.base import EngagementMessageChannel


class InboxPerson(BaseModel):
    id: UUID
    full_name: str | None
    email: str
    role: str


class InboxLastMessage(BaseModel):
    comment: str
    created_at: datetime


class InboxThread(BaseModel):
    engagement_id: UUID
    engagement_title: str
    channel: EngagementMessageChannel
    participant: InboxPerson
    last_message: InboxLastMessage | None
    unread_count: int


class InboxResponse(BaseModel):
    viewer_id: UUID
    viewer_role: Literal["client", "pentester", "service_delivery"]
    items: list[InboxThread]
    next_offset: int | None