from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_user
from app.api.routes import engagements
from app.schemas.engagement import ActivityEventRead, EngagementRead
from app.services.engagement_service import (
    get_all_engagements,
    get_engagement_activity,
)
from app.utils.db import get_db

router = APIRouter()

@router.get("/", response_model=List[EngagementRead])
async def list_engagement(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """
    Returns the list of all engagements.
    """
    return await get_all_engagements(db, user_id)

@router.get("/{engagement_id}/activity", response_model=List[ActivityEventRead])
async def get_activity_log(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """
    Returns chronological activity log for a specific engagement.
    """
    events = await get_engagement_activity(db, engagement_id, user_id)
    if not events:
        raise HTTPException(
            status__code=404, detail="Engagement not found or access denied.")
    return events