# type: ignore
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from limits.errors import StorageError
from slowapi.errors import RateLimitExceeded

import app.models  # noqa: F401 — registers all SQLAlchemy mappers before any query runs
from app.api.middleware.audit import audit_sensitive_requests
from app.api.middleware.browser_security import browser_security
from app.api.middleware.rate_limiter import (
    limiter,
    rate_limit_exceeded,
    rate_limit_unavailable,
)
from app.api.routes import (
    assistant,
    domains,
    engagements,
    findings,
    graph,
    health,
    internal,
    notifications,
    pentester,
    rag,
    reports,
    retests,
    scan_schedules,
    scans,
    service_delivery,
    summary,
    users,
)
from app.api.routes.brand_intelligence import router as brand_router
from app.realtime import stream

app = FastAPI(
    title="PenFlow API", description="Core backend API for the PenFlow platform.", version="1.0.0"
)

@app.middleware("http")
async def disable_scan_response_caching(
    request: Request,
    call_next,
):
    response = await call_next(request)

    if request.url.path.startswith(
        (
            "/api/v1/scans/",
            "/api/v1/reports/",
            "/api/v1/engagements/",
            "/api/v1/service-delivery/",
        )
    ):
        response.headers["Cache-Control"] = "no-store"

    return response

app.middleware("http")(audit_sensitive_requests)
app.middleware("http")(browser_security)
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    rate_limit_exceeded,
)
app.add_exception_handler(
    StorageError,
    rate_limit_unavailable,
)
cors_origins = [
    origin.strip() for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:3000"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_V1_PREFIX = "/api/v1"

app.include_router(health.router, prefix=API_V1_PREFIX)
app.include_router(scans.router, prefix=API_V1_PREFIX)
app.include_router(graph.router, prefix=API_V1_PREFIX)
app.include_router(stream.router, prefix=API_V1_PREFIX)
app.include_router(internal.router, prefix=API_V1_PREFIX)
app.include_router(users.router, prefix=API_V1_PREFIX)
app.include_router(summary.router, prefix=API_V1_PREFIX)
app.include_router(domains.router, prefix=API_V1_PREFIX)
app.include_router(engagements.router, prefix=API_V1_PREFIX)
app.include_router(findings.router, prefix=API_V1_PREFIX)
app.include_router(retests.router, prefix=API_V1_PREFIX)
app.include_router(pentester.router, prefix=API_V1_PREFIX)
app.include_router(reports.router, prefix=API_V1_PREFIX)
app.include_router(service_delivery.router, prefix=API_V1_PREFIX)
app.include_router(notifications.router, prefix=API_V1_PREFIX)
app.include_router(scan_schedules.router, prefix=API_V1_PREFIX)
app.include_router(brand_router, prefix=API_V1_PREFIX)
app.include_router(rag.router, prefix=API_V1_PREFIX)
app.include_router(assistant.router, prefix=API_V1_PREFIX)
