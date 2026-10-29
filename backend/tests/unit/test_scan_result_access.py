from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

import app.api.dependencies.scan_access as access
from app.api.middleware.auth import get_current_user_optional
from app.main import app
from app.models.base import ScanType
from app.repositories.scan_repo import ScanRepository
from app.utils.db import get_db

RESULT_PATHS = [
    "status",
    "pdf",
    "metrics",
    "findings",
    "assets",
    "risk-history",
    "findings-page",
    "services-page",
    "assets-page",
    "summary",
    "email-report",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("path", RESULT_PATHS)
@pytest.mark.parametrize("actor", ["anonymous", "other_client"])
async def test_private_results_deny_non_owner(
    path,
    actor,
    monkeypatch,
):
    scan_id = uuid4()
    owner_id = uuid4()

    scan = SimpleNamespace(
        id=scan_id,
        user_id=owner_id,
        scan_type=ScanType.ACTIVE_VULNERABILITY,
    )

    monkeypatch.setattr(
        ScanRepository,
        "get_scan_by_id",
        AsyncMock(return_value=scan),
    )
    monkeypatch.setattr(
        access,
        "get_user_id_by_provider_id",
        AsyncMock(return_value=uuid4()),
    )

    async def fake_db():
        yield AsyncMock()

    async def fake_user():
        if actor == "anonymous":
            return None
        return {"sub": "unrelated-user"}

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_current_user_optional] = fake_user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            url = f"/api/v1/scans/{scan_id}/{path}"

            if path == "email-report":
                response = await client.post(
                    url,
                    json={"email": "recipient@example.com"},
                )
            else:
                response = await client.get(url)

        assert response.status_code == 404

    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)