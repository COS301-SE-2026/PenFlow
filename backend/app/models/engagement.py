import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, EngagementStatus, EngagementType


# Main phase 3 request ticket.
# admins/pentesters can review and work from this later
class Engagement(Base):
    __tablename__ = "engagements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    #organisation_id: Mapped[uuid.UUID | None] = mapped_column(
    #    UUID(as_uuid=True),
    #    ForeignKey("organisations.id", ondelete = "CASCADE"),
    #    nullable=True,
    #)

    #User submitted request
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    service_delivery_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    engagement_type: Mapped[EngagementType] = mapped_column(
        Enum(
            EngagementType, 
            values_callable=lambda e: [item.value for item in e], 
            name = "engagement_type"
        ),
        nullable=False,
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium",
    )

    status: Mapped[EngagementStatus] = mapped_column(
        Enum(
            EngagementStatus,
            values_callable=lambda e: [item.value for item in e],
            name="engagement_status",
        ),
        nullable=False,
        default=EngagementStatus.REQUESTED,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)

    objective: Mapped[str|None] = mapped_column\
    (
        Text,
        nullable=True,
    )

    estimated_quote: Mapped[Decimal] = mapped_column(
        Numeric(12,2),
        nullable=False,
    )

    final_quote: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    estimated_duration_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    requested_start_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    requested_end_date: Mapped[date | None] = mapped_column\
    (
        Date,
        nullable=True,
    )

    scheduled_start_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    scheduled_end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    review_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    constraints: Mapped[str | None] = mapped_column\
    (
        Text,
        nullable=True,
    )

    primary_contact: Mapped[str | None] = mapped_column\
    (
        String(255),
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    assets = relationship(
        "EngagementAsset",
        back_populates="engagement",
        cascade="all, delete-orphan",
    )

    findings = relationship(
        "Finding",
        back_populates="engagement",
    )

    comments = relationship(
        "EngagementComment", 
        back_populates="engagement", 
        cascade="all, delete-orphan",
    )