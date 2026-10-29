from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import require_pentester
from app.api.routes.findings import upload_evidence_file
from app.models.user import User
from app.repositories.retest_repository import RetestRepository
from app.schemas.finding import EvidenceFileResponse
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


@router.post(
    "/{retest_id}/evidence",
    response_model=EvidenceFileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_retest_evidence(
    retest_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_pentester),
) -> EvidenceFileResponse:
    retest = await RetestRepository.get_by_id(
        db,
        retest_id=retest_id,
    )

    if retest is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Retest was not found.",
        )

    return await upload_evidence_file(
        finding_id=retest.finding_id,
        retest_id=retest_id,
        file=file,
        db=db,
        user=user,
    )