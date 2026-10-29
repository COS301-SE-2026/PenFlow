import hashlib
import hmac
import os
import time
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from httpx import ASGITransport, AsyncClient
from limits.errors import StorageError
from slowapi.errors import RateLimitExceeded

from app.api.middleware import auth
from app.api.middleware.client_ip import get_client_ip
from app.api.middleware.rate_limiter import (
    build_limiter,
    get_authenticated_request_key,
    rate_limit_exceeded,
    rate_limit_unavailable,
)


def request(
    headers=None,
    peer="198.51.100.1",
    path="/limited/a",
):
    return Request({
        "type": "http",
        "method": "GET",
        "path": path,
        "scheme": "http",
        "server": ("test", 80),
        "query_string": b"",
        "client": (peer, 1234),
        "headers": [
            (key.lower().encode(), value.encode())
            for key, value in (headers or {}).items()
        ],
    })


def signed(
    secret,
    ip="203.0.113.8",
    path="/limited/a",
    timestamp=None,
):
    timestamp = str(
        int(time.time())
        if timestamp is None
        else timestamp
    )

    message = f"{timestamp}\nGET\n{path}\n{ip}"

    return {
        "x-penflow-client-ip": ip,
        "x-penflow-client-time": timestamp,
        "x-penflow-client-signature": hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest(),
    }


def application(limiter):
    app = FastAPI()
    app.state.limiter = limiter

    app.add_exception_handler(
        RateLimitExceeded,
        rate_limit_exceeded,
    )
    app.add_exception_handler(
        StorageError,
        rate_limit_unavailable,
    )

    async def identity(request: Request):
        authorization = request.headers.get(
            "authorization"
        )

        if authorization:
            await auth.get_current_user(
                request,
                HTTPAuthorizationCredentials(
                    scheme="Bearer",
                    credentials=authorization.split()[1],
                ),
            )

    @app.get("/limited/{item}")
    @limiter.limit("2/minute")
    async def limited(
        request: Request,
        item: str,
        actor=Depends(identity),
    ):
        return {"ok": True}

    return app


def client_for(limiter):
    return AsyncClient(
        transport=ASGITransport(
            app=application(limiter),
        ),
        base_url="http://test",
    )


@pytest.mark.asyncio
async def test_verified_identity_survives_token_rotation(
    monkeypatch,
):
    monkeypatch.setattr(
        auth,
        "decode_token",
        AsyncMock(return_value={"sub": "same-user"}),
    )

    first = request()
    second = request()

    for target, token in (
        (first, "token-one"),
        (second, "token-two"),
    ):
        await auth.get_current_user(
            target,
            HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=token,
            ),
        )

    assert (
        get_authenticated_request_key(first)
        == get_authenticated_request_key(second)
    )

    forged = request({
        "authorization": "Bearer fake",
    })

    assert get_authenticated_request_key(
        forged
    ).startswith("ip:")


def test_forwarded_headers_need_trusted_peer(
    monkeypatch,
):
    monkeypatch.setenv(
        "TRUSTED_PROXY_CIDRS",
        "10.0.0.0/24",
    )

    headers = {
        "x-forwarded-for": "1.2.3.4, 203.0.113.9",
    }

    assert (
        get_client_ip(request(headers))
        == "198.51.100.1"
    )
    assert (
        get_client_ip(
            request(headers, peer="10.0.0.10")
        )
        == "203.0.113.9"
    )


def test_signed_ip_and_tampering(monkeypatch):
    secret = "test-proxy-secret-at-least-32-bytes-long"
    monkeypatch.setenv(
        "RATE_LIMIT_PROXY_SECRET",
        secret,
    )

    headers = signed(secret)

    assert (
        get_client_ip(request(headers))
        == "203.0.113.8"
    )

    headers["x-penflow-client-ip"] = "203.0.113.9"

    with pytest.raises(HTTPException) as exc:
        get_client_ip(request(headers))

    assert exc.value.status_code == 400


@pytest.mark.parametrize(
    "variant",
    ["expired", "wrong-path", "incomplete"],
)
def test_invalid_assertions(monkeypatch, variant):
    secret = "test-proxy-secret-at-least-32-bytes-long"
    monkeypatch.setenv(
        "RATE_LIMIT_PROXY_SECRET",
        secret,
    )

    headers = (
        signed(
            secret,
            timestamp=int(time.time()) - 120,
        )
        if variant == "expired"
        else signed(secret)
    )

    if variant == "incomplete":
        del headers["x-penflow-client-time"]

    target = (
        "/limited/b"
        if variant == "wrong-path"
        else "/limited/a"
    )

    with pytest.raises(HTTPException) as exc:
        get_client_ip(
            request(headers, path=target)
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_limits_span_path_ids_and_return_retry_after(
    monkeypatch,
):
    monkeypatch.setenv("APP_ENV", "test")

    async with client_for(
        build_limiter("memory://")
    ) as client:
        assert (
            await client.get("/limited/a")
        ).status_code == 200
        assert (
            await client.get("/limited/b")
        ).status_code == 200

        response = await client.get("/limited/c")

    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"


@pytest.mark.asyncio
async def test_storage_outage_returns_503(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    limiter = build_limiter("memory://")

    def fail(*args, **kwargs):
        raise StorageError(
            RuntimeError("storage unavailable")
        )

    monkeypatch.setattr(
        limiter.limiter,
        "hit",
        fail,
    )

    async with client_for(limiter) as client:
        response = await client.get("/limited/a")

    assert response.status_code == 503


def test_production_rejects_memory(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "RATE_LIMIT_PROXY_SECRET",
        "test-proxy-secret-at-least-32-bytes-long",
    )

    with pytest.raises(
        RuntimeError,
        match="TLS Redis",
    ):
        build_limiter("memory://")


@pytest.mark.asyncio
async def test_two_limiters_share_redis(monkeypatch):
    uri = os.getenv("RATE_LIMIT_TEST_REDIS_URL")

    if not uri:
        pytest.skip(
            "Set RATE_LIMIT_TEST_REDIS_URL "
            "to run shared Redis verification"
        )

    monkeypatch.setenv("APP_ENV", "test")
    prefix = f"test-{uuid4()}"

    async with (
        client_for(
            build_limiter(uri, key_prefix=prefix)
        ) as first,
        client_for(
            build_limiter(uri, key_prefix=prefix)
        ) as second,
    ):
        assert (
            await first.get("/limited/a")
        ).status_code == 200
        assert (
            await second.get("/limited/b")
        ).status_code == 200
        assert (
            await first.get("/limited/c")
        ).status_code == 429