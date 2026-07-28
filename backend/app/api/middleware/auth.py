import logging
import os
from typing import Any, cast

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "penflow")
ISSUER = os.getenv(
    "KEYCLOAK_ISSUER",
    f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}",
).rstrip("/")

AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", "penflow-api")

JWKS_URL = f"{ISSUER}/protocol/openid-connect/certs"

_JWKS_TIMEOUT = 10.0
_jwks_cache: dict[str, Any] = {}

security = HTTPBearer(auto_error=False)


async def _get_jwks(*, force_refresh: bool = False) -> list[dict[str, Any]]:
    if force_refresh:
        _jwks_cache.clear()

    if _jwks_cache:
        return cast(list[dict[str, Any]], _jwks_cache.get("keys", []))

    async with httpx.AsyncClient(timeout=_JWKS_TIMEOUT) as client:
        res = await client.get(JWKS_URL)
        res.raise_for_status()

        jwks = res.json()

        if not isinstance(jwks, dict) or not isinstance(jwks.get("keys"), list):
            raise ValueError("Invalid JWKS response")
        
        _jwks_cache.update(jwks)

    return cast(list[dict[str, Any]], _jwks_cache["keys"])


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


def find_signing_key(
        keys: list[dict[str, Any]],
        kid: str,
) -> dict[str, Any] | None:
    for key in keys:
        if key.get("kid") == kid:
            return key

    return None


async def decode_token(token: str) -> dict[str, Any]:
    try:
        header = jwt.get_unverified_header(token)

    except JWTError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

    kid = header.get("kid")

    if not isinstance(kid, str) or not kid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    keys = await _get_jwks()
    signing_key = find_signing_key(keys, kid)

    if signing_key is None:
        keys = await _get_jwks(force_refresh=True)
        signing_key = find_signing_key(keys, kid)

    if signing_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            token,
            _to_rsa_key(signing_key),
            algorithms=["RS256"],
            issuer=ISSUER,
            audience=AUDIENCE,
        )

        return cast(dict[str, Any], payload)

    except JWTError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err
    

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
        return await decode_token(token)

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
