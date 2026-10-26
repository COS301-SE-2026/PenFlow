import hashlib
import os
from typing import Any
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from app.api.middleware.client_ip import (
    get_client_ip,
    proxy_secret,
)


def get_authenticated_request_key(
        request: Request,
) -> str:
    subject = getattr(
        request.state,
        "rate_limit_subject",
        None,
    )

    if isinstance(subject, str) and subject:
        identity = hashlib.sha256(
            subject.encode(),
        ).hexdigest()

        return f"user:{identity}"

    return f"ip:{get_client_ip(request)}"


def build_limiter(
        storage_uri: str | None = None,
        key_prefix: str = "penflow",
) -> Limiter:
    uri = storage_uri or os.getenv(
        "RATE_LIMIT_STORAGE_URI",
        "memory://",
    )

    production = (
        os.getenv("APP_ENV", "development").lower()
        == "production"
    )

    scheme = urlsplit(uri).scheme

    if scheme not in {"memory", "redis", "rediss"}:
        raise RuntimeError(
            "Unsupported rate-limit storage"
        )

    if production:
        proxy_secret()

        if scheme != "rediss":
            raise RuntimeError(
                "Production rate limiting requires TLS Redis storage"
            )

    options: dict[str, Any] = {}

    if scheme in {"redis", "rediss"}:
        options = {
            "socket_connect_timeout": 1,
            "socket_timeout": 1,
            "wrap_exceptions": True,
        }

    if scheme == "rediss":
        options.update(
            ssl_cert_reqs="required",
            ssl_check_hostname=True,
        )

    return Limiter(
        key_func=get_authenticated_request_key,
        storage_uri=uri,
        storage_options=options,
        key_prefix=key_prefix,
        key_style="endpoint",
        strategy="fixed-window",
        headers_enabled=False,
        swallow_errors=False,
        in_memory_fallback_enabled=False,
    )


async def rate_limit_exceeded(
        request: Request,
        exc: Exception,
) -> JSONResponse:
    assert isinstance(exc, RateLimitExceeded)

    retry_after = (
        exc.limit.limit.get_expiry()
        if exc.limit is not None
        else 60
    )

    return JSONResponse(
        status_code=429,
        content={
            "detail": (
                "Too many requests. Please try again later."
            ),
        },
        headers={
            "Retry-After": str(retry_after),
            "Cache-Control": "no-store",
        },
    )


async def rate_limit_unavailable(
        request: Request,
        exc: Exception,
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "detail": (
                "Request protection is temporarily "
                "unavailable. Please retry."
            ),
        },
        headers={
            "Retry-After": "5",
            "Cache-Control": "no-store",
        },
    )


limiter = build_limiter()