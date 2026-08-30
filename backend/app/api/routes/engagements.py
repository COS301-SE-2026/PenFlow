from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_user
from app.models.base import EngagementMessageChannel
from app.repositories.user_repo import get_user_id_by_provider_id
from app.schemas.engagement import (
    EngagementCreateRequest,
    EngagementCreateResponse,
    EngagementDetailResponse,
    EngagementMessageCreate,
    EngagementMessageListResponse,
    EngagementMessageResponse,
    MarkMessagesReadResponse,
)
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
    user_id = await resolve_user_id(db, current_user)

    return await EngagementService.create_engagement(
        db,
        request=request,
        client_user_id=user_id,
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
    user_id = await resolve_user_id(db, current_user)

    return await EngagementService.get_engagement_detail(
        db,
        engagement_id=engagement_id,
        user_id=user_id,
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
    user_id = await resolve_user_id(db, current_user)

    return await EngagementService.list_messages(
        db,
        engagement_id=engagement_id,
        user_id=user_id,
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
    user_id = await resolve_user_id(db, current_user)

    return await EngagementService.create_message(
        db,
        engagement_id=engagement_id,
        user_id=user_id,
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
    user_id = await resolve_user_id(db, current_user)

    return await EngagementService.mark_messages_read(
        db,
        engagement_id=engagement_id,
        user_id=user_id,
        channel=channel,
    )