import json
import os
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import magic
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_user, require_pentester
from app.models.user import User
from app.repositories.user_repo import get_user_id_by_provider_id
from app.schemas.finding import EvidenceFileResponse, FindingDetail, FindingUpdate
from app.services.finding_service import FindingService
from app.utils.db import get_db

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

MIME_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "text/plain": ".txt",
    "application/json": ".json",
    "application/pdf": ".pdf",
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

    if (declared_mime_type is not None and declared_mime_type != detected_mime):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File content does not match its declared type.",
        )

    if detected_mime == "application/json":
        try:
            json.loads(contents)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid JSON evidence file.",
            )

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
    
    storage_root = Path(
        os.getenv(
            "EVIDENCE_STORAGE_DIR",
            "/tmp/penflow-evidence",
        )
    )

    finding_dir = storage_root / str(finding_id)
    finding_dir.mkdir(parents=True, exist_ok=True)

    suffix = MIME_EXTENSIONS[detected_mime]
    stored_name = f"{uuid4()}{suffix}"
    stored_path = finding_dir / stored_name

    stored_path.write_bytes(contents)

    try:
        return await FindingService.register_evidence(
            db,
            finding_id=finding_id,
            user_id=user.id,
            file_name=file.filename or stored_name,
            file_path=str(stored_path),
            mime_type=detected_mime,
        )

    except Exception:
        stored_path.unlink(missing_ok=True)
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