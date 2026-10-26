from secrets import compare_digest
from typing import Annotated

from fastapi import Header, HTTPException

from app.utils.internal_auth import INTERNAL_WEBHOOK_SECRET


async def require_internal_worker(
        token: Annotated[
            str | None,
            Header(alias="X-Internal-Token"),
        ] = None,
) -> None:
    if token is None or not compare_digest(
        token.encode("utf-8"),
        INTERNAL_WEBHOOK_SECRET.encode("utf-8"),
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid internal credentials.",
        )