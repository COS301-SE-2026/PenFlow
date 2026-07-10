#type: ignore
import logging
import os
from typing import Any

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
REALM = os.getenv("KEYCLOAK_REALM", "penflow")
JWKS_URL = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/certs"
ISSUER = f"{KEYCLOAK_URL}/realms/{REALM}"
_JWKS_TIMEOUT = 10.0

_jwks_cache: dict[str, Any] = {}

security = HTTPBearer(auto_error=False)


async def _get_jwks() -> list[dict[str, Any]]:
    if _jwks_cache:
        return _jwks_cache.get("keys", [])

    async with httpx.AsyncClient(timeout=_JWKS_TIMEOUT) as client:
        res = await client.get(JWKS_URL)
        res.raise_for_status()
        _jwks_cache.update(res.json())

    return _jwks_cache.get("keys", [])


def _to_rsa_key(key: dict[str, Any]) -> dict[str, Any]:
    return {
        "kty": key["kty"],
        "kid": key["kid"],
        "use": key["use"],
        "n": key["n"],
        "e": key["e"],
    }


def _extract_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    if credentials is not None:
        return credentials.credentials
    return request.cookies.get("access_token")


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    token = _extract_token(request, credentials)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        keys = await _get_jwks()

        for key in keys:
            try:
                return jwt.decode(
                    token,
                    _to_rsa_key(key),
                    algorithms=["RS256"],
                    issuer=ISSUER,
                    options={"verify_aud": False},
                )
            except JWTError:
                continue

        _jwks_cache.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except HTTPException:
        raise
    except httpx.RequestError as exc:
        logger.exception("[auth] JWKS fetch failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service unreachable",
        ) from exc
    except Exception as exc:
        logger.exception("[auth] unexpected error during token validation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token validation error",
        ) from exc


async def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any] | None:
    token = _extract_token(request, credentials)
    if token is None:
        return None
    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None