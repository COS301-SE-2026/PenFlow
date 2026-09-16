#alphabetised
from datetime import datetime, time, timezone
import pytest
from app.models.base import ScanScheduleFrequency
from app.services.schedule_calculator import \
(
    ScheduleValidationError,
    calculate_next_run,
    frequency_value,
    validate_schedule,
)


#making sure calculator can handle normal strings/enuns
def test_frequency_value_enum():
    assert frequency_value(ScanScheduleFrequency.WEEKLY) == "weekly"


def test_frequency_value_string():
    assert frequency_value("monthly") == "monthly"


#Doing a test scheduling of both types, Weekly and Mponthly
def test_validate_weekly_success():
    validate_schedule\
    (
        frequency="weekly",
        run_time=time(9, 00),
        day_of_week=0, #monday
        day_of_month=None,
        timezone_name="UTC",
    )


def test_validate_monthly_success():
    validate_schedule\
    (
        frequency="monthly",
        run_time=time(9, 00),
        day_of_week=None,
        day_of_month=15,
        timezone_name="UTC",
    )


#timezone test
def test_validate_rejects_timezone():
    with pytest.raises(ScheduleValidationError, match="UTC offset"):
        validate_schedule\
        (
            frequency="weekly",
            run_time=time(9, 00, tzinfo=timezone.utc),
            day_of_week=0,
            day_of_month=None,
            timezone_name="UTC",
        )

#no seconds
def test_validate_rejects_seconds():
    with pytest.raises(ScheduleValidationError, match="minute-level"):
        validate_schedule\
        (
            frequency="weekly",
            run_time=time(9, 00, 1),
            day_of_week=0,
            day_of_month=None,
            timezone_name="UTC",
        )


#timezone name validation
def test_validate_rejects_bad_timezone():
    with pytest.raises(ScheduleValidationError, match="Unknown timezone"):
        validate_schedule\
        (
            frequency="weekly",
            run_time=time(9, 00),
            day_of_week=0,
            day_of_month=None,
            timezone_name="Not/ARealTimezone",
        )


# Weekly schedules use Python weekday values we set, so the valid range is 0 to 6.
@pytest.mark.parametrize("day_of_week", [None, -1, 7])
def test_validate_requires_valid_day(day_of_week):
    with pytest.raises(ScheduleValidationError, match="day_of_week"):
        validate_schedule\
        (
            frequency="weekly",
            run_time=time(9, 00),
            day_of_week=day_of_week,
            day_of_month=None,
            timezone_name="UTC",
        )

#not allowed weekly and monthly field
def test_validate_month_week_combo():
    with pytest.raises(ScheduleValidationError, match="day_of_month"):
        validate_schedule\
        (
            frequency="weekly",
            run_time=time(9, 00),
            day_of_week=0,
            day_of_month=10,
            timezone_name="UTC",
        )


#days limited so that short months dont experience issues with 31'sts
@pytest.mark.parametrize("day_of_month", [None, 0, 29])
def test_validate_monthly_requires_valid_day(day_of_month):
    with pytest.raises(ScheduleValidationError, match="day_of_month"):
        validate_schedule\
        (
            frequency="monthly",
            run_time=time(9, 00),
            day_of_week=None,
            day_of_month=day_of_month,
            timezone_name="UTC",
        )


#testing actual schedule logic,
def test_weekly_schedule_later_same_day():
    result = calculate_next_run\
    (
        frequency="weekly",
        run_time=time(10, 0),
        day_of_week=0,
        day_of_month=None,
        timezone_name="UTC",
        after=datetime(2026, 9, 14, 8, 0, tzinfo=timezone.utc),
    )

    assert result == datetime\
    (
        2026,
        9,
        14,
        10,
        0,
        tzinfo=timezone.utc,
    )


#similar to last test just after the scheduled time now
def test_weekly_schedule_moves_next_week():
    result = calculate_next_run\
    (
        frequency="weekly",
        run_time=time(10, 0),
        day_of_week=0,
        day_of_month=None,
        timezone_name="UTC",
        after=datetime(2026, 9, 14, 11, 0, tzinfo=timezone.utc),
    )

    assert result == datetime\
    (
        2026,
        9,
        21,
        10,
        0,
        tzinfo=timezone.utc,
    )


#testing time conversion, we store UTC
def test_weekly_schedule_timezone():
    result = calculate_next_run\
    (
        frequency="weekly",
        run_time=time(9, 30),
        day_of_week=0,
        day_of_month=None,
        timezone_name="Africa/Johannesburg",
        after=datetime(2026, 9, 14, 5, 0, tzinfo=timezone.utc),
    )

    assert result == datetime\
    (
        2026,
        9,
        14,
        7,
        30,
        tzinfo=timezone.utc,
    )

#correct month
def test_monthly_schedule_runs_in_current_month():
    result = calculate_next_run\
    (
        frequency="monthly",
        run_time=time(10, 0),
        day_of_week=None,
        day_of_month=20,
        timezone_name="UTC",
        after=datetime(2026, 9, 16, 8, 0, tzinfo=timezone.utc),
    )

    assert (result == datetime
    (
        2026,
        9,
        20,
        10,
        0,
        tzinfo=timezone.utc,
    ))


#month logic
def test_monthly_schedule_moves_to_next_month():
    result = calculate_next_run\
    (
        frequency="monthly",
        run_time=time(10, 0),
        day_of_week=None,
        day_of_month=10,
        timezone_name="UTC",
        after=datetime(2026, 9, 16, 8, 0, tzinfo=timezone.utc),
    )

    assert result == datetime\
    (
        2026,
        10,
        10,
        10,
        0,
        tzinfo=timezone.utc,
    )


#testing end of year
def test_monthly_schedule_rollover_new_year():
    result = calculate_next_run\
    (
        frequency="monthly",
        run_time=time(10, 0),
        day_of_week=None,
        day_of_month=10,
        timezone_name="UTC",
        after=datetime(2026, 12, 20, 8, 0, tzinfo=timezone.utc),
    )

    assert (result == datetime\
    (
        2027,
        1,
        10,
        10,
        0,
        tzinfo=timezone.utc,
    ))


#lack of timezone
def test_calculate_rejects_reference_without_timezone():
    with pytest.raises\
    (
        ScheduleValidationError,
        match="reference datetime must include a timezone",
    ):
        calculate_next_run\
        (
            frequency="weekly",
            run_time=time(10, 0),
            day_of_week=0,
            day_of_month=None,
            timezone_name="UTC",
            after=datetime(2026, 9, 14, 8, 0),
        )