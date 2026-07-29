from unittest.mock import AsyncMock

import pytest

from app.api.routes.health import health_check

@pytest.mark.asyncio
async def test_health_check_database_connected():
    db = AsyncMock()

    result = await health_check(db)

    db.execute.assert_awaited_once()
    assert result == {
        "status" : "ok",
        "api_version" : "1.0.0",
        "database": "connected",
    }

@pytest.mark.asyncio
async def test_health_check_database_disconnected():
    db = AsyncMock()
    db.execute.side_effect = Exception("connection refused")

    result =  await health_check(db)

    db.execute.assert_awaited_once()
    assert result == {
        "status": "ok",
        "api_version" :"1.0.0",
        "database" : "disconnected",
    }