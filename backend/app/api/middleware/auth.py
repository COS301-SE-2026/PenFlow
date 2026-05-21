#type: ignore
import logging
import os
from typing import Any

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
REALM = os.getenv("KEYCLOAK_REALM", "penflow")
JWKS_URL = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/certs"

_jwks_cache: dict[str, Any] = {}

security = HTTPBearer()


async def _get_jwks() -> dict[str, Any]:
    if _jwks_cache:
        return _jwks_cache

    async with httpx.AsyncClient() as client:
        res = await client.get(JWKS_URL)
        res.raise_for_status()
        _jwks_cache.update(res.json())

    return _jwks_cache


def _find_rsa_key(jwks: dict[str, Any], kid: str) -> dict[str, Any]:
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
    return {}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    token = credentials.credentials

    try:
        header = jwt.get_unverified_header(token)
        jwks = await _get_jwks()
        rsa_key = _find_rsa_key(jwks, header.get("kid", ""))

        if not rsa_key:
            _jwks_cache.clear()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find matching public key",
            )

        payload: dict[str, Any] = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return payload

    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
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
