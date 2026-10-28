import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class EvidenceFile(Base):
    __tablename__ = "evidence_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)

    file_path: Mapped[str] = mapped_column(Text, nullable=False)

    storage_backend: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="local",
        server_default="local",
    )

    sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    size_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    quarantine_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
        server_default="pending",
    )

    scan_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    next_scan_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    scanned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    scan_message: Mapped[str | None] = mapped_column(String(255))

    scanner_version: Mapped[str | None] = mapped_column(String(255))

    finding = relationship("Finding", back_populates="evidence_files")