# type: ignore
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_user
from app.repositories.user_repo import get_or_create_user
from app.utils.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])

CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/me")
async def provision_user(
    current_user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    try:
        return await get_or_create_user(
            db=db,
            auth_provider_id=current_user["sub"],
            email=current_user.get("email", ""),
            full_name=current_user.get("name"),
        )
    except Exception as exc:
        logger.exception("[users/me] DB provisioning failed for sub=%s", current_user.get("sub"))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to provision user",
        ) from exc
