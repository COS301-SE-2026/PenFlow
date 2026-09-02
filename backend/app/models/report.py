import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, ReportStatus


class Report(Base):
    __tablename__ = "reports"
    __table_args__= (
        CheckConstraint(
            "(scan_id IS NOT NULL AND engagement_id IS NULL) "
            "OR (scan_id IS NULL AND engagement_id IS NOT NULL)",
            name="ck_report_scan_or_engagement",
        ),
        UniqueConstraint("engagement_id", "version", name="uq_reports_engagement_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    scan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scans.id", ondelete="CASCADE"),
        unique=True,
        nullable=True,
        index=True,
    )

    engagement_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[ReportStatus] = mapped_column(
        Enum(
            ReportStatus,
            values_callable=lambda enum: [item.value for item in enum],
            name="report_status",
        ),
        nullable=False,
        default=ReportStatus.PENDING,
    )

    pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    scan = relationship("Scan", back_populates="report")
    engagement = relationship("Engagement", back_populates="reports")