from datetime import datetime, time
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.base import ScanType

ScheduleFrequency = Literal["weekly", "monthly"]

def validate_timezone_name(val: str) -> str:
    try:
        ZoneInfo(val)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Unknown timezone.") from exc

    return val


def validate_run_time(val: time) -> time:
    if val.tzinfo is not None:
        raise ValueError("run_time must be local and not have a UTC offset")

    if val.second != 0 or val.microsecond != 0:
        raise ValueError("Scheduled Scans can only support minute-level precision")

    return val


class ScanScheduleCreate(BaseModel):
    verified_domain_id: UUID
    scan_type: Literal[ScanType.ACTIVE_VULNERABILITY] = ScanType.ACTIVE_VULNERABILITY
    frequency: ScheduleFrequency
    run_time: time
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    day_of_month: int | None = Field(default=None, ge=1, le=28)
    timezone: str = Field(
        default="Africa/Johannesburg",
        min_length=1,
        max_length=64,
    )

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, val:str) -> str:
        return validate_timezone_name(val)

    @field_validator("run_time")
    @classmethod
    def validate_time(cls, val: time) -> time:
        return validate_run_time(val)

    @model_validator(mode="after")
    def validate_recurrence(self) -> "ScanScheduleCreate":
        if self.frequency == "weekly":
            if self.day_of_week is None:
                raise ValueError("day_of_week required for weekly schedule")

            if self.day_of_month is not None:
                raise ValueError("day_of_month must be null for weekly schedule")

        if self.frequency == "monthly":
            if self.day_of_month is None:
                raise ValueError("day_of_month required for monthly schedule")

            if self.day_of_week is not None:
                raise ValueError("day_of_week must be null for monthly schedule")

        return self


class ScanScheduleUpdate(BaseModel):
    frequency: ScheduleFrequency | None = None
    run_time: time | None = None
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    day_of_month: int | None = Field(default=None, ge=1, le=28)
    timezone: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
    )
    is_active: bool | None = None

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, val: str | None) -> str | None:
        if val is None:
            return None
        
        return validate_timezone_name(val)

    @field_validator("run_time")
    @classmethod
    def validate_time(cls, val: time | None) -> time | None:
        if val is None:
            return None
        
        return validate_run_time(val)


class ScanScheduleResponse(BaseModel):
    id: UUID
    user_id: UUID
    verified_domain_id: UUID
    scan_type: ScanType
    frequency: ScheduleFrequency
    run_time: time
    day_of_week: int | None
    day_of_month: int | None
    timezone: str
    is_active: bool
    next_run_at: datetime
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config =ConfigDict(from_attributes=True)