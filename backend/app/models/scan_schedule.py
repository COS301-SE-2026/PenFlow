import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    SmallInteger,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, ScanScheduleFrequency, ScanType


class ScanSchedule(Base):
    __tablename__ = "scan_schedules"

    __table_args__ = (

        CheckConstraint(
            "frequency IN ('weekly', 'monthly')",
            name="ck_scan_schedule_supported_frequency",
        ),
        CheckConstraint(
            "day_of_week IS NULL OR day_of_week BETWEEN 0 AND 6",
            name="ck_scan_schedule_day_of_week_range",
        ),
        CheckConstraint(
            "day_of_month IS NULL OR day_of_month BETWEEN 1 AND 28",
            name="ck_scan_schedule_day_of_month_range",
        ),
        CheckConstraint(
            """
            (
                frequency='weekly' AND day_of_week IS NOT NULL
                AND day_of_month IS NULL
            )
            OR
            (
                frequency='monthly' AND day_of_month IS NOT NULL
                AND day_of_week IS NULL
            )
            """,
            name="ck_scan_schedule_recurrence_fields",
        ),
        UniqueConstraint(
            "verified_domain_id",
            "scan_type",
            name = "uq_scan_schedules_verified_domain_scan_type",
        ),
    )

    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )

    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    verified_domain_id = Column(
        UUID(as_uuid=True),
        ForeignKey("verified_domains.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    scan_type = Column(
        Enum(
            ScanType,
            values_callable = lambda enum: [item.value for item in enum],
            name = "scan_type",
        ),
        nullable=False,
        default=ScanType.ACTIVE_VULNERABILITY,
    )

    frequency = Column(
        Enum(
            ScanScheduleFrequency,
            values_callable = lambda enum: [item.value for item in enum],
            name = "scan_schedule_frequency",
        ),
        nullable = False,
    )

    run_time = Column(
        Time(timezone=False),
        nullable=False,
    )

    day_of_week = Column(
        SmallInteger,
        nullable=True,
    )

    day_of_month = Column(
        SmallInteger,
        nullable=True,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    next_run_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    last_run_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    timezone = Column(
        String(64),
        nullable=False,
        default="Africa/Johannesburg",
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default = lambda: datetime.now(timezone.utc),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default = lambda: datetime.now(timezone.utc),
        onupdate = lambda: datetime.now(timezone.utc),
    )

    user = relationship(
        "User",
        foreign_keys=[user_id],
    )

    verified_domain = relationship(
        "VerifiedDomain",
        foreign_keys=[verified_domain_id],
    )

    scans = relationship(
        "Scan",
        back_populates="schedule",
        passive_deletes=True,
    )