import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, FindingReviewStatus, FindingStatus, Severity


class Finding(Base):
    __tablename__ = "findings"
    __table_args__= (
        CheckConstraint(
            "(scan_id IS NOT NULL) OR (engagement_id IS NOT NULL)",
            name="ck_finding_has_scan_or_engagement",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )

    scan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("scans.id", ondelete="CASCADE"), 
        nullable=True, 
        index=True
    )

    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("assets.id", ondelete="SET NULL"), 
        nullable=True,
        index=True
    )

    service_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("services.id", ondelete="SET NULL"), 
        nullable=True,
        index=True,
    )

    engagement_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    engagement_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("engagement_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    source: Mapped[str] = mapped_column(String(100), nullable=False)

    status: Mapped[FindingStatus] = mapped_column(
        Enum(
            FindingStatus,
            values_callable=lambda enum: [item.value for item in enum],
            name="finding_status",
        ),
        nullable=False,
        default=FindingStatus.OPEN,
        index=True,
    )

    review_status: Mapped[FindingReviewStatus | None] = mapped_column(
        Enum(
            FindingReviewStatus,
            values_callable=lambda e: [item.value for item in e],
            name="finding_review_status",
        ),
        nullable=True,
    )

    cvss_score: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)

    cve_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    severity: Mapped[Severity] = mapped_column(
        Enum(
            Severity,
            values_callable=lambda enum: [item.value for item in enum],
            name="finding_severity",
        ),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)

    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB, 
        nullable=False, 
        default=dict,
    )

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        default=lambda: datetime.now(timezone.utc)
    )

    scan = relationship("Scan", back_populates="findings")
    asset = relationship("Asset", back_populates="findings")
    engagement = relationship("Engagement", back_populates="findings")
    engagement_asset = relationship("EngagementAsset")

    evidence_files = relationship(
        "EvidenceFile",
        back_populates="finding",
        cascade="all, delete-orphan",
    )

    retests = relationship(
        "FindingRetest",
        back_populates="finding",
        cascade="all, delete-orphan",
    )
