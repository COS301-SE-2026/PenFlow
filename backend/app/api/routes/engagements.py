from typing import Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.middleware.auth import get_current_user
from app.repositories.user_repo import get_user_id_by_provider_id
from app.schemas.engagement import \
(
    EngagementCreateRequest,
    EngagementCreateResponse,
    EngagementDetailResponse,
)
from app.services.engagement_service import EngagementService
from app.utils.db import get_db


router = APIRouter(prefix="/engagements", tags=["Engagement Requests"])


#keycloak provides subject then we resolve to DB usr
@router.post("/", response_model=EngagementCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_engagement_request\
(
    request: EngagementCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> EngagementCreateResponse:

    user_id = await get_user_id_by_provider_id\
    (
        db,
        current_user["sub"],
    )

    if user_id is None:
        raise HTTPException\
        (
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not present.",
        )

    return await EngagementService.create_engagement\
    (
        db,
        request=request,
        client_user_id=user_id,
    )


#Used for frontend and backend to receive details
@router.get("/{engagement_id}", response_model=EngagementDetailResponse)
async def get_engagement_request\
(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> EngagementDetailResponse:

    user_id = await get_user_id_by_provider_id\
    (
        db,
        current_user["sub"],
    )

    if user_id is None:
        raise HTTPException\
        (
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not present.",
        )

    return await EngagementService.get_engagement\
    (
        db,
        engagement_id=engagement_id,
        user_id=user_id,
    )