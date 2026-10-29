from unittest.mock import AsyncMock

import pytest
from fastapi import Request
from starlette.responses import Response

from app.api.middleware.browser_security import (
    browser_security,
    cookie_mutation_allowed,
)


def make_request(
    method="POST",
    cookie=True,
    **headers,
):
    values = (
        {"cookie": "access_token=test"}
        if cookie
        else {}
    )
    values.update(headers)

    return Request({
        "type": "http",
        "method": method,
        "path": "/api/v1/findings",
        "headers": [
            (key.encode(), value.encode())
            for key, value in values.items()
        ],
    })


@pytest.fixture(autouse=True)
def origins(monkeypatch):
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "https://app.example.com",
    )


@pytest.mark.parametrize(
    "origin",
    [
        "https://evil.example",
        "https://app.example.com.evil.example",
        "https://other.example.com",
        "http://app.example.com",
        "https://app.example.com:444",
        "null",
        "not a URL",
        "https://user@app.example.com",
        "https://app.example.com/path",
    ],
)
def test_rejects_foreign_or_invalid_origin(origin):
    assert not cookie_mutation_allowed(
        make_request(origin=origin)
    )


@pytest.mark.parametrize(
    "method",
    ["POST", "PUT", "PATCH", "DELETE"],
)
def test_accepts_trusted_origin(method):
    assert cookie_mutation_allowed(
        make_request(
            method=method,
            origin="https://app.example.com",
        )
    )


def test_referer_fallback():
    assert cookie_mutation_allowed(
        make_request(
            referer="https://app.example.com/findings/1",
        )
    )


def test_invalid_origin_cannot_fall_back():
    assert not cookie_mutation_allowed(
        make_request(
            origin="null",
            referer="https://app.example.com/",
        )
    )


def test_missing_headers():
    assert not cookie_mutation_allowed(make_request())


def test_explicit_bearer_path_remains_available():
    assert cookie_mutation_allowed(
        make_request(
            authorization="Bearer explicit-token",
        )
    )


def test_other_auth_scheme_does_not_bypass():
    assert not cookie_mutation_allowed(
        make_request(authorization="Basic encoded")
    )


def test_anonymous_public_requests_remain_available():
    assert cookie_mutation_allowed(
        make_request(cookie=False)
    )


def test_safe_get():
    assert cookie_mutation_allowed(
        make_request(method="GET")
    )


def test_spoofed_host_is_not_trusted():
    assert not cookie_mutation_allowed(
        make_request(
            origin="https://evil.example",
            host="evil.example",
        )
    )


@pytest.mark.asyncio
async def test_blocked_request_never_reaches_handler():
    call_next = AsyncMock()

    response = await browser_security(
        make_request(),
        call_next,
    )

    assert response.status_code == 403
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    call_next.assert_not_awaited()


@pytest.mark.asyncio
async def test_allowed_request_headers():
    call_next = AsyncMock(
        return_value=Response("ok"),
    )

    response = await browser_security(
        make_request(
            origin="https://app.example.com",
        ),
        call_next,
    )

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    call_next.assert_awaited_once()