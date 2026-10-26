from datetime import datetime, time, timezone

import pytest

from app.services.schedule_calculator import (
    ScheduleValidationError,
    calculate_next_run,
)


def test_weekly_happy():
    result = (calculate_next_run
    (
        frequency="weekly",
        run_time=time(9,0),
        day_of_week=0,
        day_of_month=None,
        timezone_name="Africa/Johannesburg",
        after=datetime(2026,9,30,8,0,tzinfo=timezone.utc),
    ))

    assert result == datetime(2026,10,5,7,0,tzinfo=timezone.utc)


def test_monthly_happy():
    result = (calculate_next_run
    (
        frequency="monthly",
        run_time=time(9,0),
        day_of_week=None,
        day_of_month=5,
        timezone_name="Africa/Johannesburg",
        after=datetime(2026,9,30,8,0,tzinfo=timezone.utc),
    ))

    assert result == datetime(2026,10,5,7,0,tzinfo=timezone.utc)


def test_schedule_sad():
    with pytest.raises(ScheduleValidationError):
        (calculate_next_run
        (
            frequency="daily",
            run_time=time(9,0),
            day_of_week=None,
            day_of_month=None,
            timezone_name="Africa/Johannesburg",
        ))