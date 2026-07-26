import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import Base


class DetectedTechnology(Base):
    __tablename__ = "detected_technologies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), index=True)
    service_id = Column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="SET NULL"), index=True
    )
    technology_type = Column(String(50), nullable=False)
    product = Column(String(255), nullable=False)
    version = Column(String(255))
    confidence = Column(Numeric(4, 3))
    detection_source = Column(String(100))
    evidence = Column(JSONB, nullable=False, default=dict)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
