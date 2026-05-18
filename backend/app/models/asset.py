import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint('scan_id','identifier','asset_type', name='uq_scan_identifier_type'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id",ondelete="CASCADE"), nullable=False, index=True)
    identifier = Column(String(255), nullable=False)
    asset_type = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    scan = relationship("Scan", back_populates="assets")
    findings = relationship("Finding", back_populates="assets")