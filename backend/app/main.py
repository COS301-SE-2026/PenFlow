# type: ignore
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

import app.models  # noqa: F401 — registers all SQLAlchemy mappers before any query runs
from app.api.routes import domains, health, internal, scans, summary, users
from app.realtime import stream
from app.api.middleware.rate_limiter import limiter

app = FastAPI(
    title="PenFlow API", description="Core backend API for the PenFlow platform.", version="1.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
