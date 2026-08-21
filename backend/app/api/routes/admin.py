from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import require_admin
from app.models.user import User
from app.schemas.admin import AdminUserListResponse, AdminUserRoleFilter
from app.services.admin_service import AdminService
from app.utils.db import get_db

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/users",
    response_model=AdminUserListResponse,
    summary="List users for admin dashboard",
)
async def get_admin_users(
    search: Annotated[str | None, Query(max_length=255)] = None,
    role: AdminUserRoleFilter | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> AdminUserListResponse:
    return await AdminService.list_users(
        db,
        search=search,
        role=role,
        limit=limit,
        offset=offset,
    )