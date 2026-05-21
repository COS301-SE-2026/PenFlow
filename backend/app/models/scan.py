# type: ignore
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, ScanStatus


class Scan(Base):
    __tablename__ = "scans"
    CASCADE_ALL = "all, delete-orphan"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    #I'm going to ommit organisation_id and user_id for now until auth
    domain = Column(String(255),nullable=False, index=True)
    email = Column(String(255))
    status = Column(
        Enum(ScanStatus, values_callable=lambda enum: [item.value for item in enum],
             name="scan_status"),
        nullable=False,
        default=ScanStatus.QUEUED,
        index=True,
    )
    progress = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False,
    default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)

    assets = relationship("Asset", back_populates="scan", cascade=CASCADE_ALL)
    findings = relationship("Finding", back_populates="scan", cascade=CASCADE_ALL)
    sources = relationship("ScanSource", back_populates="scan", cascade=CASCADE_ALL)
    report = relationship(
        "Report", back_populates="scan", cascade="all, delete-orphan", uselist=False
    )
