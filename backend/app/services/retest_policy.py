from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status


def require_retest_window(
    scheduled_end_date: date | None,
    *,
    today: date | None = None,
) -> None:
    if scheduled_end_date is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Retesting requires a scheduled end date.",
        )

    current_date = (
        today if today is not None
        else datetime.now(timezone.utc).date()
    )
    deadline = scheduled_end_date + timedelta(days=7)

    if current_date > deadline:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "The retesting window has expired. "
                f"Retesting was available through {deadline.isoformat()} (UTC)."
            ),
        )