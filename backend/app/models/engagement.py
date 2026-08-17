import uuid
from datetime import date, datetime, timezone
from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, EngagementAssetType, EngagementStatus, EngagementType


# Main phase 3 request ticket.
# admins/pentesters can review and work from this later
class Engagement(Base):
    __tablename__ = "engagements"
    CASCADE_ALL = "all, delete-orphan"

    id: Mapped[uuid.UUID] = mapped_column\
    (
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    client_user_id: Mapped[uuid.UUID] = mapped_column\
    (
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    assigned_pentester_id: Mapped[uuid.UUID | None] = mapped_column\
    (
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[EngagementStatus] = mapped_column\
    (
        Enum\
        (
            EngagementStatus,
            values_callable=lambda e: [item.value for item in e],
            name="engagement_status",
        ),
        nullable=False,
        default=EngagementStatus.SCOPING,
        index=True,
    )

    engagement_type: Mapped[EngagementType] = mapped_column\
    (
        Enum\
        (
            EngagementType,
            values_callable=lambda e: [item.value for item in e],
            name="engagement_type",
        ),
        nullable=False,
        index=True,
    )

    objective: Mapped[str] = mapped_column\
    (
        Text,
        nullable=False,
    )

    start_date: Mapped[date | None] = mapped_column\
    (
        Date,
        nullable=True,
    )

    end_date: Mapped[date | None] = mapped_column\
    (
        Date,
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

    created_at: Mapped[datetime] = mapped_column\
    (
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column\
    (
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    assets: Mapped[list["EngagementAsset"]] = relationship\
    (
        "EngagementAsset",
        back_populates="engagement",
        cascade=CASCADE_ALL,
    )

# The declared scope for the request.
# assets the client is giving permission to test
class EngagementAsset(Base):
    __tablename__ = "engagement_assets"

    id: Mapped[uuid.UUID] = mapped_column\
    (
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    engagement_id: Mapped[uuid.UUID] = mapped_column\
    (
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    type: Mapped[EngagementAssetType] = mapped_column\
    (
        Enum\
        (
            EngagementAssetType,
            values_callable=lambda e: [item.value for item in e],
            name="engagement_asset_type",
        ),
        nullable=False,
        index=True,
    )

    value: Mapped[str] = mapped_column\
    (
        String(2048),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column\
    (
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    engagement: Mapped[Engagement] = relationship\
    (
        "Engagement",
        back_populates="assets",
    )