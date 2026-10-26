import json
import logging
from io import BytesIO
from typing import Any
from uuid import UUID

import magic
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.api.middleware.auth import get_current_user, require_pentester
from app.models.evidence_file import EvidenceFile
from app.models.user import User
from app.repositories.user_repo import get_user_id_by_provider_id
from app.schemas.finding import EvidenceFileResponse, FindingDetail, FindingUpdate
from app.services.evidence_storage_service import EvidenceStorageService
from app.services.finding_service import FindingService
from app.utils.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/findings", tags=["Findings"])

MB_SIZE = 10
MAX_SIZE = MB_SIZE * 1024 * 1024
ALLOWED_TYPES = {
    "image/png",
    "image/jpeg",
    "text/plain",
    "application/json",
    "application/pdf",
}


def validate_image(contents: bytes) -> None:
    try:
        with Image.open(BytesIO(contents)) as image:
            image.verify()

    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid or corrupted image",
        ) from exc



def validate_evidence_file(
    contents: bytes,
    declared_mime_type: str | None,
) -> str:
    detected_mime = magic.from_buffer(
        contents,
        mime=True,
    )

    if detected_mime not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported evidence file type.",
        )

    if declared_mime_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported declared evidence type.",
        )


    if (
        declared_mime_type == "application/json"
        and detected_mime == "text/plain"
    ):
        try:
            contents.decode("utf-8")
            json.loads(contents)
            detected_mime = "application/json"
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid JSON evidence file.",
            )

    if declared_mime_type != detected_mime:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File content does not match its declared type.",
        )

    if detected_mime == "application/json":
        try:
            json.loads(contents.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid JSON evidence file.",
            )

    elif detected_mime == "text/plain":
        try:
            contents.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Text evidence must be valid UTF-8.",
            ) from exc

    return detected_mime


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


@router.get("/{finding_id}", response_model=FindingDetail)
async def get_finding(
    finding_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> FindingDetail:
    user_id = await resolve_user_id(db, current_user)

    return await FindingService.get_finding(
        db,
        finding_id=finding_id,
        user_id=user_id,
    )


@router.patch("/{finding_id}", response_model=FindingDetail)
async def update_finding(
    finding_id: UUID,
    request: FindingUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_pentester),
) -> FindingDetail:
    return await FindingService.update_finding(
        db,
        finding_id=finding_id,
        user_id=user.id,
        request=request,
    )


@router.post(
    "/{finding_id}/evidence", 
    response_model=EvidenceFileResponse, 
    status_code=status.HTTP_201_CREATED
)
async def upload_finding_evidence(
    finding_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_pentester),
) -> EvidenceFileResponse:
    finding = await FindingService.require_editable_finding(
        db,
        finding_id=finding_id,
        user_id=user.id,
    )

    engagement_id = finding.engagement_id

    if engagement_id is None:
        raise HTTPException(404, "Finding was not found")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported evidence file type.",
        )

    contents = await file.read(MAX_SIZE + 1)

    if len(contents) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Evidence files may not exceed {MB_SIZE} MB.",
        )

    if not contents:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Evidence file cannot be empty.",
        )

    detected_mime = validate_evidence_file(
        contents,
        declared_mime_type=file.content_type,
    )

    if detected_mime in {"image/png", "image/jpeg"}:
        validate_image(contents)

    storage = EvidenceStorageService()

    try:
        stored = await run_in_threadpool(
            storage.store,
            engagement_id=engagement_id,
            finding_id=finding_id,
            contents=contents,
            mime_type=detected_mime,
        )

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Evidence storage write failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Evidence storage is temporarily unavailable",
        ) from exc

    name = (
        (file.filename or "evidence")
        .replace("\\", "/")
        .rsplit("/", 1)[-1]
    )
    name = (
        "".join(char for char in name if char.isprintable())[:255]
        or "evidence"
    )

    try:
        return await FindingService.register_evidence(
            db,
            finding_id=finding_id,
            user_id=user.id,
            file_name=name,
            file_path=stored.file_path,
            mime_type=detected_mime,
            storage_backend=stored.storage_backend,
            sha256=stored.sha256,
            size_bytes=stored.size_bytes,
        )

    except Exception:
        try:
            await db.rollback()

            persisted = await db.scalar(
                select(EvidenceFile.id).where(
                    EvidenceFile.file_path == stored.file_path
                )
            )

            if persisted is None:
                await run_in_threadpool(
                    storage.delete,
                    storage_backend=stored.storage_backend,
                    file_path=stored.file_path,
                )

        except Exception:
            logger.exception(
                "Evidence cleanup failed; reconciliation is required"
            )

        raise


@router.delete("/{finding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_finding(
    finding_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_pentester)
) -> None:
    await FindingService.delete_manual_finding(
        db,
        finding_id=finding_id,
        user_id=user.id,
    )


@router.patch("/{finding_id}/verify", response_model=FindingDetail)
async def verify_finding(
    finding_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_pentester),
) -> FindingDetail:
    return await FindingService.verify_automated_finding(
        db,
        finding_id=finding_id,
        user_id=user.id,
    )