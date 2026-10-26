import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Literal, cast
from uuid import UUID, uuid4

import jwt
from fastapi import Depends, HTTPException, Request
from jwt.exceptions import PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_user_optional
from app.models.base import ScanType
from app.models.scan import Scan
from app.repositories.scan_repo import ScanRepository
from app.repositories.user_repo import get_user_id_by_provider_id
from app.utils.db import get_db

_SECRET = os.environ["GUEST_SCAN_TOKEN_SECRET"]

if len(_SECRET.encode()) < 32:
    raise RuntimeError(
        "GUEST_SCAN_TOKEN_SECRET must contain at least 32 bytes"
    )

GUEST_TOKEN_TTL = 24 * 60 * 60
_ISSUER = "penflow-guest"
_AUDIENCE = "penflow-scan-results"

Permission = Literal["read", "email"]

DbSession = Annotated[AsyncSession, Depends(get_db)]
OptionalUser = Annotated[
    dict[str, Any] | None,
    Depends(get_current_user_optional),
]


def issue_guest_token(scan_id: UUID) -> str:
    now = datetime.now(timezone.utc)

    token = jwt.encode(
        {
            "iss": _ISSUER,
            "aud": _AUDIENCE,
            "sub": str(scan_id),
            "iat": int(now.timestamp()),
            "exp": int(
                (
                    now + timedelta(seconds=GUEST_TOKEN_TTL)
                ).timestamp()
            ),
            "jti": str(uuid4()),
            "scope": "read email",
        },
        _SECRET,
        algorithm="HS256",
    )

    if not isinstance(token, str):
        raise RuntimeError(
            "Guest token signing returned an invalid value"
        )

    return token


def valid_guest_token(
        token: str | None,
        scan_id: UUID,
        permission: Permission,
) -> bool:
    if not token:
        return False

    try:
        claims = jwt.decode(
            token,
            _SECRET,
            algorithms=["HS256"],
            audience=_AUDIENCE,
            issuer=_ISSUER,
            options={
                "require": ["exp", "iat", "sub", "iss", "aud"],
            },
        )

        scope = claims.get("scope")

        return (
            claims["sub"] == str(scan_id)
            and isinstance(scope, str)
            and permission in scope.split()
        )

    except (PyJWTError, ValueError, TypeError):
        return False


async def require_scan_permission(
        scan_id: UUID,
        request: Request,
        db: AsyncSession,
        current_user: dict[str, Any] | None,
        permission: Permission,
) -> Scan:
    scan = await ScanRepository.get_scan_by_id(db, scan_id)

    if scan is not None:
        if scan.user_id is not None:
            if current_user is not None:
                user_id = await get_user_id_by_provider_id(
                    db,
                    current_user["sub"],
                )

                if user_id is not None and user_id == scan.user_id:
                    return scan

        elif scan.scan_type == ScanType.PASSIVE_CTEM:
            token = request.headers.get("X-Scan-Token")

            if valid_guest_token(
                token,
                cast(UUID, scan.id), 
                permission,
            ):
                return scan

    raise HTTPException(
        status_code=404,
        detail="Scan not found",
    )


async def require_scan_read(
        scan_id: UUID,
        request: Request,
        db: DbSession,
        current_user: OptionalUser,
) -> Scan:
    return await require_scan_permission(
        scan_id,
        request,
        db,
        current_user,
        "read",
    )


async def require_scan_email(
        scan_id: UUID,
        request: Request,
        db: DbSession,
        current_user: OptionalUser,  
) -> Scan:
    return await require_scan_permission(
        scan_id,
        request,
        db,
        current_user,
        "email",
    )