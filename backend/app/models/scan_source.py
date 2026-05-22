import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class ScanSourceStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


class ScanSource(Base):
    __tablename__ = "scan_sources"
    __table_args__ = (
        UniqueConstraint("scan_id", "source_name", name="uq_scan_source_name"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    source_name = Column(String(100), nullable=False)
    status: Column[str] = Column(
        Enum(ScanSourceStatus, values_callable=lambda enum: [item.value for item in enum],
             name="scan_source_status"),
        nullable=False,
        default=ScanSourceStatus.PENDING,
    )
    raw_result = Column(JSONB)
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    scan = relationship("Scan", back_populates="sources")