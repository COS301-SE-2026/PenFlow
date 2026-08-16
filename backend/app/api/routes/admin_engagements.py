from uuid import UUID
from fastapi import APIrouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_user 
from app.schemas.engagement import (
    EngagementCounts,
    EngagementListItem,
    EngagementListResponse,
    EngagementPagination,
    EngagementSortField,
    SortOrder,
)
from app.services.engagement_service import get_admin_engagements_paginated 
from app.utils.db import get_db 

router = APIRouter()

@router.get("/admin/all", response_model=EngagementListResponse)
async def list_all_engagements_admin(
    search: str | None = Query(default=None, description="Search by engagement title"),
    status: str | None = Query(default=None, description="Filter by EngagementStatus"),
    pentester_id: UUID | None = Query(default=None, description="Filter by specific pentester UUID")
    assignment_status: str | None = Query(default=None, description="'assigned', 'unassigned', or 'all'"),
    sort: EngagementSortField = Query(default=EngagementSortField.CREATED_AT),
    order: SortOrder = Query(default=SortOrder.DESC),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Admin endpoint to view, filter and assign engagements."""

    engagements, total, raw_counts = await get_admin_engagements_paginated(
        db=db,
        search=search,
        status=status,
        pentester_id=pentester_id,
        assignment_status=assignment_status,
        sort=sort,
        order=order,
        limit=limit,
        offset=offset,
    )

    total_all = sum(raw_counts.values())
    counts = EngagementCounts(
        all=total_all,
        requested=raw_counts.get("requested", 0),
        scoping=raw_counts.get("scoping", 0),
        in_progress=raw_counts.get("in_progress", 0),
        review=raw_counts.get("review", 0),
        completed=raw_counts.get("competed", 0),
        cancelled=raw_counts.get("cancelled", 0),
    )

    items = []
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
            client_name="Client Name",
            asset_count=0,
            target_date=None 
        ))

    