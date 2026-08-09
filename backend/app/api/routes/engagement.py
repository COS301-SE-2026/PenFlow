from fastapi import APIRouter, Depends, HTTPException
from typing import List 
from app.schemas.engagement import EngagementRead, ActivityEventRead
from app.services.engagement_service import EngagementService
from app.api.dependencies import get_engagement_service

router = APIRouter()

@router.get("/", response_model=List[EngagementRead])
async def get_engagement_summary(
    service: EngagementService = Depends(get_engagement_service)
):
    """
    Returns the list of all engagements to populate the dashboard view.
    """
    return await service.get_all_engagements()

@router.get("/{engagement_id}/activity", response_model=List[ActivityEventRead])
async def get_activity_log(
    engagement_id: str,
    service: EngagementService = Depends(get_engagement_service)
):
    """
    Returns chronological activity log for a specific engagement when clicked.
    """
    events = await service.get_engagement_activity(engagement_id)
    if not events:
        raise HTTPException(status__code=404, detail="Engagement not found or no activity.")
    return events