# type: ignore
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

import app.models  # noqa: F401 — registers all SQLAlchemy mappers before any query runs
from app.api.middleware.rate_limiter import limiter
from app.api.routes import (
    domains,
    engagements,
    findings,
    health,
    internal,
    notifications,
    pentester,
    retests,
    scans,
    service_delivery,
    summary,
    users,
)
from app.realtime import stream

app = FastAPI(
    title="PenFlow API", description="Core backend API for the PenFlow platform.", version="1.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
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
app.include_router(stream.router, prefix=API_V1_PREFIX)
app.include_router(internal.router, prefix=API_V1_PREFIX)
app.include_router(users.router, prefix=API_V1_PREFIX)
app.include_router(summary.router, prefix=API_V1_PREFIX)
app.include_router(domains.router, prefix=API_V1_PREFIX)
app.include_router(engagements.router, prefix=API_V1_PREFIX)
app.include_router(findings.router, prefix=API_V1_PREFIX)
app.include_router(retests.router, prefix=API_V1_PREFIX)
app.include_router(pentester.router, prefix=API_V1_PREFIX)
app.include_router(service_delivery.router, prefix=API_V1_PREFIX)
app.include_router(notifications.router, prefix=API_V1_PREFIX)
