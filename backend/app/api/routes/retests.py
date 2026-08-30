from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import require_pentester
from app.models.user import User
from app.schemas.retest import RetestListItem, RetestUpdate
from app.services.retest_service import RetestService
from app.utils.db import get_db

router = APIRouter(prefix="/retests", tags=["Re-tests"])


@router.patch("/{retest_id}", response_model=RetestListItem)
async def update_retest(
    retest_id: UUID,
    request: RetestUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_pentester),
) -> RetestListItem:
    return await RetestService.update_retest(
        db,
        retest_id=retest_id,
        user_id=user.id,
        request=request,
    )