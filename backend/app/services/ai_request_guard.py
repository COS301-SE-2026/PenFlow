import asyncio
import hashlib
import logging
import os
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import HTTPException
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

AI_REQUEST_TIMEOUT_SECONDS = 120
AI_LOCK_SECONDS = 180

_RELEASE = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


@asynccontextmanager
async def ai_request_slot(user_id: object) -> AsyncIterator[None]:
    uri = os.getenv("RATE_LIMIT_STORAGE_URI", "")

    if not uri.startswith(("redis://", "rediss://")):
        raise HTTPException(
            503,
            "AI concurrency protection requires Redis.",
            headers={"Cache-Control": "no-store"},
        )

    options: dict[str, Any] = {
        "socket_connect_timeout": 1,
        "socket_timeout": 1,
        "decode_responses": True,
    }

    if uri.startswith("rediss://"):
        options.update(
            ssl_cert_reqs="required",
            ssl_check_hostname=True,
        )

    client = Redis.from_url(uri, **options)
    identity = hashlib.sha256(str(user_id).encode()).hexdigest()
    key = f"penflow:ai:active:{identity}"
    token = secrets.token_hex(32)
    acquired = False

    try:
        try:
            acquired = bool(
                await client.set(
                    key,
                    token,
                    nx=True,
                    ex=AI_LOCK_SECONDS,
                )
            )
        except RedisError:
            raise HTTPException(
                503,
                "AI request protection is temporarily unavailable.",
                headers={
                    "Retry-After": "5",
                    "Cache-Control": "no-store",
                },
            ) from None

        if not acquired:
            raise HTTPException(
                429,
                "An AI request is already running for your account.",
                headers={
                    "Retry-After": "5",
                    "Cache-Control": "no-store",
                },
            )

        try:
            async with asyncio.timeout(AI_REQUEST_TIMEOUT_SECONDS):
                yield
        except TimeoutError:
            raise HTTPException(
                504,
                "The AI request timed out. Please try again.",
                headers={"Cache-Control": "no-store"},
            ) from None

    finally:
        try:
            if acquired:
                try:
                    await client.eval(_RELEASE, 1, key, token)
                except RedisError:
                    logger.warning("AI concurrency lease release failed")
        finally:
            await client.aclose()