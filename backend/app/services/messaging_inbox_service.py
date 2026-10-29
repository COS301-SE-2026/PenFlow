from typing import Literal, cast

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.pentester_profile_repository import PentesterProfileRepository
from app.schemas.messaging_inbox import (
    InboxLastMessage,
    InboxPerson,
    InboxResponse,
    InboxThread,
)

INBOX_QUERY = text("""
WITH eligible AS (
    SELECT e.id, e.title, e.updated_at,
           'client_service_delivery' AS channel,
           CASE WHEN e.service_delivery_id = :user_id
                THEN e.requested_by ELSE e.service_delivery_id END AS participant_id
    FROM engagements e
    WHERE e.service_delivery_id IS NOT NULL
      AND ((:role = 'client' AND e.requested_by = :user_id)
        OR (:role = 'service_delivery' AND e.service_delivery_id = :user_id))

    UNION ALL

    SELECT e.id, e.title, e.updated_at,
           'service_delivery_pentester' AS channel,
           CASE WHEN e.service_delivery_id = :user_id
                THEN e.assigned_to ELSE e.service_delivery_id END AS participant_id
    FROM engagements e
    WHERE e.service_delivery_id IS NOT NULL AND e.assigned_to IS NOT NULL
      AND ((:role = 'pentester' AND e.assigned_to = :user_id)
        OR (:role = 'service_delivery' AND e.service_delivery_id = :user_id))
)
SELECT e.id AS engagement_id, e.title AS engagement_title, e.channel,
       p.id AS participant_id, p.full_name, p.email, p.role AS participant_role,
       latest.comment, latest.created_at, unread.unread_count
FROM eligible e
JOIN users p ON p.id = e.participant_id
LEFT JOIN LATERAL (
    SELECT c.comment, c.created_at
    FROM engagement_comments c
    WHERE c.engagement_id = e.id AND c.channel::text = e.channel
    ORDER BY c.created_at DESC, c.id DESC
    LIMIT 1
) latest ON TRUE
LEFT JOIN LATERAL (
    SELECT count(*) AS unread_count
    FROM engagement_comments c
    WHERE c.engagement_id = e.id AND c.channel::text = e.channel
      AND c.recipient_id = :user_id AND c.is_read = FALSE
) unread ON TRUE
ORDER BY latest.created_at DESC NULLS LAST, e.updated_at DESC, e.id, e.channel
LIMIT :limit OFFSET :offset
""")


async def list_messaging_inbox(
    db: AsyncSession,
    user: User,
    *,
    limit: int = 100,
    offset: int = 0,
) -> InboxResponse:
    if user.role not in {"client", "pentester", "service_delivery"}:
        raise HTTPException(403, "Messaging access required.")

    if user.role == "pentester":
        profile = await PentesterProfileRepository.get_by_user_id(
            db,
            user_id=user.id,
        )
        if profile is None or not profile.is_active:
            raise HTTPException(403, "Pentester account is inactive.")

    result = await db.execute(
        INBOX_QUERY,
        {
            "user_id": user.id,
            "role": user.role,
            "limit": limit + 1,
            "offset": offset,
        },
    )
    rows = result.mappings().all()

    return InboxResponse(
        viewer_id=user.id,
        viewer_role=cast(
            Literal["client", "pentester", "service_delivery"],
            user.role,
        ),
        next_offset=offset + limit if len(rows) > limit else None,
        items=[
            InboxThread(
                engagement_id=row["engagement_id"],
                engagement_title=row["engagement_title"],
                channel=row["channel"],
                participant=InboxPerson(
                    id=row["participant_id"],
                    full_name=row["full_name"],
                    email=row["email"],
                    role=row["participant_role"],
                ),
                last_message=InboxLastMessage(
                    comment=row["comment"],
                    created_at=row["created_at"],
                )
                if row["created_at"] is not None
                else None,
                unread_count=row["unread_count"],
            )
            for row in rows[:limit]
        ],
    )