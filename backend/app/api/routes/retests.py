from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_user
from app.repositories.user_repo import get_user_id_by_provider_id
from app.schemas.retest import RetestListItem, RetestUpdate
from app.services.retest_service import RetestService
from app.utils.db import get_db

router = APIRouter(prefix="/retests", tags=["Re-tests"])

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


@router.patch("/{retest_id}", response_model=RetestListItem)
async def update_retest(
    retest_id: UUID,
    request: RetestUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> RetestListItem:
    user_id = await resolve_user_id(db, current_user)

    return await RetestService.update_retest(
        db,
        retest_id=retest_id,
        user_id=user_id,
        request=request,
    )