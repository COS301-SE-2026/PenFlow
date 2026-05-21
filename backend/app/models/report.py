import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.models.report_status import ReportStatus


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), unique=True, nullable=False)
    task_id = Column(String(255))
    status = Column(Enum(ReportStatus, values_callable=lambda enum: [item.value for item in enum]), nullable=False, default=ReportStatus.PENDING)
    pdf_path = Column(Text)
    generated_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    error_message = Column(Text)

    scan = relationship("Scan", back_populates="report")