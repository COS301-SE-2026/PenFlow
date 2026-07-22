import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, Severity, FindingStatus


class Finding(Base):
    __tablename__ = "findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False,
    index=True)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), index=True)
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id", ondelete="SET NULL"), index=True)
    source = Column(String(100), nullable=False) #expl HaveIBeenPwned
    status = Column(
        Enum(Findingstatus, values_callable=lambda enum: [item.value for item in enum],
             name="finding_status"),
        nullable=False,
        default=Findingstatus.OPEN,
    )
    cvss_score = Column(Numeric(3, 1))
    cve_id = Column(String(50))
    severity = Column(
        Enum(Severity, values_callable=lambda enum: [item.value for item in enum],
             name="finding_severity"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text)
    recommendation = Column(Text)
    evidence = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False,
    default=lambda: datetime.now(timezone.utc))

    scan = relationship("Scan", back_populates="findings")
    asset = relationship("Asset", back_populates="findings")