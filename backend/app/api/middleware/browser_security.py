import os
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def origin_tuple(
        value: str,
        origin_only: bool = False,
) -> tuple[str, str, int] | None:
    if value != value.strip():
        return None

    try:
        url = urlsplit(value)

        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or (
                origin_only
                and (
                    url.path not in {"", "/"}
                    or url.query
                    or url.fragment
                )
            )
        ):
            return None

        default_port = 443 if url.scheme == "https" else 80

        return (
            url.scheme,
            url.hostname.lower(),
            url.port if url.port is not None else default_port,
        )

    except ValueError:
        return None


def cookie_mutation_allowed(request: Request) -> bool:
    if (
        request.method in SAFE_METHODS
        or not request.cookies.get("access_token")
    ):
        return True

    scheme, _, token = request.headers.get(
        "authorization",
        "",
    ).partition(" ")

    if scheme.lower() == "bearer" and token.strip():
        return True

    if request.headers.get("sec-fetch-site") == "cross-site":
        return False

    configured = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000",
    )

    allowed = {
        origin_tuple(value.strip(), origin_only=True)
        for value in configured.split(",")
        if value.strip()
    } - {None}

    origin = request.headers.get("origin")

    if origin is not None:
        return origin_tuple(
            origin,
            origin_only=True,
        ) in allowed
    referer = request.headers.get("referer")

    return (
        referer is not None
        and origin_tuple(referer) in allowed
    )


async def browser_security(
        request: Request, 
        call_next: RequestResponseEndpoint,
) -> Response:
    
    response: Response
    if not cookie_mutation_allowed(request):
        response = JSONResponse(
            status_code=403,
            content={
                "detail": "Cross-site or unverifiable request rejected",
            },
            headers={"Cache-Control": "no-store"},
        )

    else:
        response = await call_next(request)


    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = (
        "strict-origin-when-cross-origin"
    )

    if request.cookies.get("access_token"):
        response.headers["Cache-Control"] = "no-store"

    return response