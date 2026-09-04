from calendar import monthrange
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.models.base import ScanScheduleFrequency

WEEKDAY_NAMES = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}

class ScheduleValidationError(ValueError):
    pass


def frequency_value(frequency: ScanScheduleFrequency | str) -> str:
    if isinstance(frequency, ScanScheduleFrequency):
        return frequency.value

    return str(frequency)


def validate_schedule(
        *,
        frequency: ScanScheduleFrequency | str,
        run_time: time,
        day_of_week: int | None,
        day_of_month: int | None,
        timezone_name: str,
) -> None:
    value = frequency_value(frequency)

    if value not in {"weekly", "monthly"}:
        raise ScheduleValidationError(
            "Only weekly and monthly scheduled are supported"
        )

    if run_time.tzinfo is not None:
        raise ScheduleValidationError(
            "run_time must not contain a UTC offset"
        )

    if run_time.second != 0 or run_time.microsecond != 0:
        raise ScheduleValidationError(
            "Scheduled scans only support minute-level precision"
        )

    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ScheduleValidationError(
            "Unknown timezone"
        ) from exc

    if value == "weekly":
        if day_of_week is None or not 0 <= day_of_week <= 6:
            raise ScheduleValidationError(
                "Weekly schedules require day_of_week betwen 0 and 6"
            )

        if day_of_month is not None:
            raise ScheduleValidationError(
                "Weekly schedules cannot define day_of_month"
            )

    if value == "monthly":
        if day_of_month is None or not 1 <= day_of_month <= 28:
            raise ScheduleValidationError(
                "Monthly schedules require day_of_month between 1 and 28"
            )

        if day_of_week is not None:
            raise ScheduleValidationError(
                "Monthly schedules cannot define day_of_week"
            )


def localize_wall_time(
        candidate_date: date,
        run_time: time,
        schedule_timezone: ZoneInfo,
) -> datetime:
    naive_candidate = datetime.combine(candidate_date, run_time)
    candidate = naive_candidate.replace(tzinfo=schedule_timezone)

    normalized = candidate.astimezone(timezone.utc).astimezone(schedule_timezone)

    if normalized.replace(tzinfo=None) != naive_candidate:
        return normalized

    return candidate


def monthly_candidate(
        *,
        year: int,
        month: int,
        day: int,
        run_time: time,
        schedule_timezone: ZoneInfo,
) -> datetime:
    last_day = monthrange(year, month)[1]

    return localize_wall_time(
        date(year, month, min(day, last_day)),
        run_time,
        schedule_timezone,
    )


def next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1

    return year, month +1


def calculate_next_run(
        *,
        frequency: ScanScheduleFrequency | str,
        run_time: time,
        day_of_week: int | None,
        day_of_month: int | None,
        timezone_name: str,
        after: datetime | None = None,
) -> datetime:
    validate_schedule(
        frequency=frequency,
        run_time=run_time,
        day_of_week=day_of_week,
        day_of_month=day_of_month,
        timezone_name=timezone_name
    )

    schedule_timezone = ZoneInfo(timezone_name)
    reference = after or datetime.now(timezone.utc)

    if reference.tzinfo is None or reference.utcoffset() is None:
        raise ScheduleValidationError(
            "The reference datetime must include a timezone"
        )

    reference_utc = reference.astimezone(timezone.utc)
    local_reference = reference_utc.astimezone(schedule_timezone)

    value = frequency_value(frequency)

    if value == "weekly":
        assert day_of_week is not None

        days_ahead = (day_of_week - local_reference.weekday()) % 7

        candidate_date = (local_reference.date() + timedelta(days=days_ahead))

        candidate = localize_wall_time(
            candidate_date,
            run_time,
            schedule_timezone,
        )

        if candidate.astimezone(timezone.utc) <= reference_utc:
            candidate = localize_wall_time(
                candidate_date + timedelta(days=7),
                run_time,
                schedule_timezone,
            )

        return candidate.astimezone(timezone.utc)

    assert day_of_month is not None

    candidate = monthly_candidate(
        year=local_reference.year,
        month=local_reference.month,
        day=day_of_month,
        run_time=run_time,
        schedule_timezone=schedule_timezone,
    )

    if candidate.astimezone(timezone.utc) <= reference_utc:
        year, month = next_month(
            local_reference.year,
            local_reference.month
        )

        candidate = monthly_candidate(
            year=year,
            month=month,
            day=day_of_month,
            run_time=run_time,
            schedule_timezone=schedule_timezone,
        )

    return candidate.astimezone(timezone.utc)