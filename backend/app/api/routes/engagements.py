from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_user
from app.models.base import (
    EngagementMessageChannel,
    EngagementStatus,
    FindingReviewStatus,
    FindingStatus,
    Severity,
)
from app.models.user import User
from app.repositories.engagement_repository import EngagementRepository
from app.repositories.report_repository import get_by_engagement_and_version 
from app.repositories.user_repo import get_user_id_by_provider_id
from app.schemas.engagement import (
    ActivityListResponse,
    EngagementCreateRequest,
    EngagementCreateResponse,
    EngagementDetailResponse,
    EngagementListResponse,
    EngagementMessageCreate,
    EngagementMessageListResponse,
    EngagementMessageResponse,
    EngagementSortField,
    MarkMessagesReadResponse,
    SortOrder,
)
from app.schemas.finding import FindingCreate, FindingListItem, FindingListResponse
from app.schemas.retest import RetestListResponse
from app.services.engagement_service import EngagementService
from app.services.report_service import queue_engagement_report_generation
from app.utils.db import get_db

router = APIRouter(prefix="/engagements", tags=["Engagements"])


async def resolve_user(
    db: AsyncSession,
    current_user: dict[str, Any],
) -> User:
    user_id = await get_user_id_by_provider_id(
        db,
        current_user["sub"]
    )

    if user_id:
        user = await EngagementRepository.get_user_by_id(db, user_id)
        if user:
            return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="User not present.",
    )


@router.post(
    "/",
    response_model=EngagementCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create client engagement request",
)

async def create_engagement_request(
    request: EngagementCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> EngagementCreateResponse:
    user = await resolve_user(db, current_user)

    return await EngagementService.create_engagement(
        db,
        request=request,
        client_user_id=user.id,
    )

@router.get(
    "",
    response_model=EngagementListResponse,
    summary="List engagements for user",
)
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
    user = await resolve_user(db, current_user)

    return await EngagementService.list_engagements(
        db,
        user_id=user.id,
        user_role=user.role,
        engagement_status=engagement_status,
        search=search,
        sort=sort,
        order=order,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{engagement_id}",
    response_model=EngagementDetailResponse,
    summary="Get engagement detail",
)
async def get_engagement(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> EngagementDetailResponse:
    user = await resolve_user(db, current_user)

    return await EngagementService.get_engagement_detail(
        db,
        engagement_id=engagement_id,
        user_id=user.id,
    )


@router.get(
    "/{engagement_id}/findings",
    response_model=FindingListResponse,
    summary="List findings for an engagement",
)
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
    user = await resolve_user(db, current_user)

    return await EngagementService.list_findings(
        db,
        engagement_id=engagement_id,
        user_id=user.id,
        source=source,
        severity=severity,
        finding_status=finding_status,
        review_status=review_status,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/{engagement_id}/findings",
    response_model=FindingListItem,
    status_code=status.HTTP_201_CREATED,
    summary="Create manual finding for an engagement",
)
async def create_engagement_finding(
    engagement_id: UUID,
    request: FindingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> FindingListItem:
    user = await resolve_user(db, current_user)

    return await EngagementService.create_manual_finding(
        db,
        engagement_id=engagement_id,
        user_id=user.id,
        request=request,
    )


@router.get(
    "/{engagement_id}/retests",
    response_model=RetestListResponse,
    summary="List retests for an engagement",
)
async def get_engagement_retests(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> RetestListResponse:
    user = await resolve_user(db, current_user)

    return await EngagementService.list_retests(
        db,
        engagement_id=engagement_id,
        user_id=user.id,
    )


@router.get(
    "/{engagement_id}/messages",
    response_model=EngagementMessageListResponse,
    summary="List engagement messages",
)
async def get_engagement_messages(
    engagement_id: UUID,
    channel: EngagementMessageChannel,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> EngagementMessageListResponse:
    user = await resolve_user(db, current_user)

    return await EngagementService.list_messages(
        db,
        engagement_id=engagement_id,
        user_id=user.id,
        channel=channel,
    )


@router.post(
    "/{engagement_id}/messages",
    response_model=EngagementMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create engagement message",
)
async def create_engagement_message(
    engagement_id: UUID,
    request: EngagementMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> EngagementMessageResponse:
    user = await resolve_user(db, current_user)

    return await EngagementService.create_message(
        db,
        engagement_id=engagement_id,
        user_id=user.id,
        request=request,
    )


@router.patch(
        "/{engagement_id}/messages/read", 
        response_model=MarkMessagesReadResponse,
        summary="Marks viewed messages as read",
)
async def mark_engagement_messages_read(
    engagement_id: UUID,
    channel: EngagementMessageChannel,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> MarkMessagesReadResponse:
    user = await resolve_user(db, current_user)

    return await EngagementService.mark_messages_read(
        db,
        engagement_id=engagement_id,
        user_id=user.id,
        channel=channel,
    )

@router.get(
    "/{engagement_id}/activity",
    response_model=ActivityListResponse,
    summary="List engagement activity",
)
async def get_engagement_activity(
    engagement_id: UUID,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> ActivityListResponse:
    user = await resolve_user(db, current_user)

    return await EngagementService.list_activity(
        db,
        engagement_id=engagement_id,
        user_id=user.id,
        limit=limit,
    )

@router.get(
    "/{engagement_id}/report",
    summary="Get engagement report",
)
async def get_engagement_report(
    engagement_id: UUID, 
    version: int = 1,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user)):

    user = await resolve_user(db, current_user)

    report = await get_by_engagement_and_version(db, engagement_id, version) 
    if not report:
        raise HTTPException(status_code=404, detail="Report not found for this engagement.")
    return {
        "id": report.id, 
        "engagement_id": report.engagement_id, 
        "version": report.version, 
        "status": report.status, 
        "pdf_path": report.pdf_path, 
        "generated_at": report.generated_at,
    }

@router.post(
    "/{engagement_id}/report/retry",
    summary="Retry engagement report generation",
)
async def retry_engagement_report(
    engagement_id: UUID,
    version: int = 1, 
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    user = await resolve_user(db, current_user)

    try:
        return await queue_engagement_report_generation(db, engagement_id, version)
    except Exception as e: 
        raise HTTPException(status_code=500, detail=str(e))
