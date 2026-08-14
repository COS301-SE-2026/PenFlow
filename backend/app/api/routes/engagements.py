from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_user
from app.models.base import EngagementStatus, FindingReviewStatus, FindingStatus, Severity
from app.repositories.user_repo import get_user_id_by_provider_id
from app.schemas.engagement import (
    ActivityListResponse,
    EngagementDetailResponse,
    EngagementListResponse,
    EngagementMessageCreate,
    EngagementMessageListResponse,
    EngagementMessageResponse,
    EngagementSortField,
    SortOrder,
)
from app.schemas.finding import FindingCreate, FindingListItem, FindingListResponse
from app.schemas.retest import RetestListResponse
from app.services.engagement_service import EngagementService
from app.utils.db import get_db

router = APIRouter(prefix="/engagements", tags=["Engagements"])


async def resolve_user_id(
        db: AsyncSession,
        current_user: dict[str, Any],
) -> UUID:
    user_id = await get_user_id_by_provider_id(
        db,
        current_user["sub"],
    )

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not present.",
        )

    return user_id


@router.get("", response_model=EngagementListResponse)
async def get_engagements(
    engagement_status: Annotated[
        EngagementStatus | None,
        Query(alias="status"),
    ] = None,
    search: Annotated[
        str | None,
        Query(max_length=255),
    ] = None,
    sort: EngagementSortField = EngagementSortField.UPDATED_AT,
    order: SortOrder = SortOrder.DESC,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> EngagementListResponse:
    user_id = await resolve_user_id(db, current_user)

    return await EngagementService(
        db,
        user_id=user_id,
        engagement_status=engagement_status,
        search=search,
        sort=sort,
        order=order,
        limit=limit,
        offset=offset,
    )


@router.get("/{engagement_id}", response_model=EngagementDetailResponse)
async def get_engagement(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> EngagementDetailResponse:
    user_id = await resolve_user_id(db, current_user)

    return await EngagementService.get_engagement_detail(
        db,
        engagement_id=engagement_id,
        user_id=user_id,
    )


@router.get("/{engagement_id}/findings", response_model=FindingListResponse)
async def get_engagement_findings(
    engagement_id: UUID,
    source: Annotated[str | None, Query(max_length=100)] = None,
    severity: Severity | None = None,
    finding_status: Annotated[
        FindingStatus | None,
        Query(alias="status"),
    ] = None,
    review_status: FindingReviewStatus | None = None,
    search: Annotated[
        str | None,
        Query(max_length=255),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> FindingListResponse:
    user_id = await resolve_user_id(db, current_user)

    return await EngagementService.list_findings(
        db,
        engagement_id=engagement_id,
        user_id=user_id,
        source=source,
        severity=severity,
        finding_status=finding_status,
        review_status=review_status,
        search=search,
        limit=limit,
        offset=offset,
    )