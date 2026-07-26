import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base

class Service(Base):
    __tablename__ = "services"
    __table_args__ = (
        UniqueConstraint("scan_id", "host", "port", "protocol", name="uq_service_scan_host_port_protocol"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    protocol = Column(String(20), nullable=False)
    service_name = Column(String(100))
    product = Column(String(255))
    version = Column(String(255))
    banner = Column(Text)
    state = Column(String(50), nullable=False, default="open")
    tls_enabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )