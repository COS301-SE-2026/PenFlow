from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_user
from app.schemas.engagement import ActivityListResponse, ActivityItemresponse, EngagementRead
from app.services.engagement_service import (
    get_all_engagements,
    get_engagement_activity,
)
from app.utils.db import get_db

router = APIRouter()

@router.get("/", response_model=EngagementListResponse)
async def list_engagement(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    engagements = await get_all_engagements(db, user_id)

    item = []
    for eng in engagements:
        items.append(EngagementListItem(
            id=eng.id,
            title=eng.title,
            engagement_type=eng.engagement_type,
            priority=eng.priority,
            status=eng.status,
            requested_start_date=eng.requested_start_date,
            estimated_duration_days=eng.estimated_duration_days,
            updated_at=eng.updated_at,
            client_name="Current User",
            asset_count=0,
            target_date=None
        ))

    return EngagementListResponse(
        items=items,
        counts=EngagementCounts(all=len(item), requested=0, scoping=0, in_progress=0, review=0, completed=0, cancelled=0),
        pagination=EngagementPagination(total=len(items), limit=100, offset=0, has_more=False)
    )

@router.get("/{engagement_id}/activity", response_model=ActivityListResponse)
async def get_activity_log(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    logs = await get_engagement_activity(db, engagement_id)

    """
    Returns chronological activity log for a specific engagement.
    """

    if not logs:
        raise HTTPException(
            status__code=404, detail="No activity found for this engagement."
        )

    items = []
    for log in logs:
        items.append(ActivityItemResponse(
            id=log.id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            actor=None,
            metadata=log.metadata_,
            created_at=log.created_at
        ))
    return ActivityListResponse(items=items)