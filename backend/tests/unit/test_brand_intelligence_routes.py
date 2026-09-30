from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4
import pytest
from fastapi import HTTPException
from app.api.routes.brand_intelligence import (
    get_brand_candidates,
    trigger_brand_scan,
)


def _user():
    return{"sub":"jerry-123"}


@pytest.mark.asyncio
@patch(
    "app.api.routes.brand_intelligence.BrandIntelligenceService.trigger_monitoring_run",
    new_callable=AsyncMock,
)

@patch(
    "app.api.routes.brand_intelligence.get_user_id_by_provider_id",
    new_callable=AsyncMock,
)

async def test_trigger_route(mock_user,mock_trigger):
    db = AsyncMock()
    user_id = uuid4()
    domain_id = uuid4()
    mock_user.return_value = user_id
    mock_trigger.return_value = (SimpleNamespace
    (
        id=uuid4()
    ))
    result = await (trigger_brand_scan
    (
        domain_id,
        _user(),
        db,
    ))
    assert result is mock_trigger.return_value


@pytest.mark.asyncio
@patch(
    "app.api.routes.brand_intelligence.get_user_id_by_provider_id",
    new_callable=AsyncMock,
)

async def test_trigger_no_user(mock_user):
    db = AsyncMock()
    mock_user.return_value = None
    with pytest.raises(HTTPException) as error:
        await trigger_brand_scan(
            uuid4(),
            _user(),
            db,
        )
    assert error.value.status_code == 404


@pytest.mark.asyncio
@patch(
    "app.api.routes.brand_intelligence.BrandIntelligenceService.get_monitoring_overview",
    new_callable=AsyncMock,
)

@patch(
    "app.api.routes.brand_intelligence.get_user_id_by_provider_id",
    new_callable=AsyncMock,
)

async def test_get_brand(mock_user,mock_get):
    db = AsyncMock()
    user_id = uuid4()
    mock_user.return_value = user_id
    mock_get.return_value = (SimpleNamespace
    (
        id=uuid4()
    ))
    result = await (get_brand_candidates
    (
        uuid4(),
        _user(),
        db,
    ))

    assert result is mock_get.return_value


@pytest.mark.asyncio
@patch(
    "app.api.routes.brand_intelligence.BrandIntelligenceService.get_monitoring_overview",
    new_callable=AsyncMock,
)

@patch(
    "app.api.routes.brand_intelligence.get_user_id_by_provider_id",
    new_callable=AsyncMock,
)

async def test_get_brand_missing(mock_user,mock_get):
    db = AsyncMock()
    mock_user.return_value = uuid4()
    mock_get.return_value = None
    with pytest.raises(HTTPException) as error:
        await get_brand_candidates(
            uuid4(),
            _user(),
            db,
        )

    assert error.value.status_code == 404