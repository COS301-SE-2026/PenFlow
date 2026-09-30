from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.base import (
    DomainVerificationStatus,
    ScanType,
)
from app.repositories.domain_repository import DomainRepository
from app.repositories.scan_schedule_repository import ScanScheduleRepository
from app.services.scan_schedule_service import ScanScheduleService


@pytest.mark.asyncio
async def test_create_happy(monkeypatch):
    db = AsyncMock()
    user_id = uuid4()
    domain_id = uuid4()

    domain = (SimpleNamespace
    (
        id=domain_id,
        status=DomainVerificationStatus.VERIFIED,
    ))

    request = (SimpleNamespace
    (
        verified_domain_id=domain_id,
        scan_type=ScanType.ACTIVE_VULNERABILITY,
        frequency="weekly",
        run_time=__import__("datetime").time(9,0),
        day_of_week=0,
        day_of_month=None,
        timezone="Africa/Johannesburg",
    ))

    schedule = (SimpleNamespace
    (
        id=uuid4(),
        is_active=True,
    ))

    monkeypatch.setattr(
        DomainRepository,
        "get_by_id",
        AsyncMock(return_value=domain),
    )

    monkeypatch.setattr(
        ScanScheduleRepository,
        "create_schedule",
        AsyncMock(return_value=schedule),
    )

    result = await (ScanScheduleService.create_schedule
    (
        db,
        user_id,
        request,
    ))

    assert result is schedule
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_sad(monkeypatch):
    db = AsyncMock()

    request = (SimpleNamespace
    (
        verified_domain_id=uuid4(),
    ))

    monkeypatch.setattr(
        DomainRepository,
        "get_by_id",
        AsyncMock(return_value=None),
    )

    with pytest.raises(HTTPException) as error:
        await (ScanScheduleService.create_schedule
        (
            db,
            uuid4(),
            request,
        ))

    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_get_sad(monkeypatch):
    db = AsyncMock()

    monkeypatch.setattr(
        ScanScheduleRepository,
        "get_for_user",
        AsyncMock(return_value=None),
    )

    with pytest.raises(HTTPException) as error:
        await (ScanScheduleService.get_schedule
        (
            db,
            uuid4(),
            uuid4(),
        ))

    assert error.value.status_code == 404