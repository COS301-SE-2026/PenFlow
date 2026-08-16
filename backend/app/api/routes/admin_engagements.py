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