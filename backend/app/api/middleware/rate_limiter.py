import hashlib
import os

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

REDIS_URL = os.getenv("REDIS_URL", "memory://")

def get_authenticated_request_key(
        request: Request,
) -> str:
    authorization = request.headers.get(
        "authorization",
        "",
    )

    scheme, _, credentials = authorization.partition(" ")

    token = (
        credentials.strip()
        if scheme.casefold() == "bearer"
        else ""
    )

    if not token:
        token = request.cookies.get("access_token", "")

    if token:
        fingerprint = hashlib.sha256(
            token.encode("utf-8"),
        ).hexdigest()

        return f"authenticated:{fingerprint}"

    return f"anonymous:{get_remote_address(request)}"

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=REDIS_URL,
)