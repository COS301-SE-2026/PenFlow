
#Shared test fixtures: real DB session + FastAPI client for integration tests (unit tests mock 
# their own db instead)
# Shared test fixtures for the backend tests.
# This file provides fixtures for:
# 1. Real database sessions for integration tests
# 2. FastAPI test client with dependency overrides
# 3. Authentication override for testing protected endpoints
# Unit tests should mock their own dependencies instead of using these fixtures.
import os
import sys
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

# Shared test fixtures: real DB session + FastAPI client for integration tests
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
from app.main import app  # noqa: E402
from app.api.middleware.auth import get_current_user  # noqa: E402
from app.utils.db import get_db  # noqa: E402

# Configure test database URL
# Convert postgresql:// to postgresql+asyncpg:// for async support
TEST_DATABASE_URL = os.getenv("DATABASE_URL")

if TEST_DATABASE_URL.startswith("postgresql://"):
    TEST_DATABASE_URL = TEST_DATABASE_URL.replace(
        "postgresql://",
        "postgresql+asyncpg://",
        1,
    )

# Create async engine for test database
# NullPool prevents connection pooling issues between tests
engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
)

# Session factory for creating database sessions in tests
TestingSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def test_client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="https://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()