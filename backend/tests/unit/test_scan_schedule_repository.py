from datetime import datetime, time, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import pytest
from app.models.base import (
    ScanScheduleFrequency,
    ScanType,
)
from app.repositories.scan_schedule_repository import ScanScheduleRepository


@pytest.mark.asyncio
async def test_create_happy():
    db = AsyncMock()
    db.add = MagicMock()

    domain_id = uuid4()
    user_id = uuid4()

    result = await (ScanScheduleRepository.create_schedule
    (
        db,
        user_id=user_id,
        verified_domain_id=domain_id,
        scan_type=ScanType.ACTIVE_VULNERABILITY,
        frequency=ScanScheduleFrequency.WEEKLY,
        run_time=time(9,0),
        day_of_week=0,
        day_of_month=None,
        timezone_name="Africa/Johannesburg",
        next_run_at=datetime(2026,10,5,7,0,tzinfo=timezone.utc),
    ))

    assert result.user_id == user_id
    assert result.verified_domain_id == domain_id
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_get_happy():
    db = AsyncMock()
    schedule = MagicMock()

    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = schedule
    db.execute.return_value = query_result

    result = await (ScanScheduleRepository.get_for_user
    (
        db,
        uuid4(),
        uuid4(),
    ))

    assert result is schedule


@pytest.mark.asyncio
async def test_get_sad():
    db = AsyncMock()

    query_result = MagicMock()
    query_result.scalar_one_or_none.return_value = None
    db.execute.return_value = query_result

    result = await (ScanScheduleRepository.get_for_user
    (
        db,
        uuid4(),
        uuid4(),
    ))

    assert result is None