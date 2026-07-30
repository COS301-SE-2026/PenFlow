import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, ScanStatus, ScanType


class Scan(Base):
    __tablename__ = "scans"
    CASCADE_ALL = "all, delete-orphan"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # I'm going to omit organisation_id for now until auth
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task_id = Column(String(255))
    domain = Column(String(255), nullable=False, index=True)

    verified_domain_id = Column(
        UUID(as_uuid=True),
        ForeignKey("verified_domains.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    schedule_id = Column(
        UUID(as_uuid=True),
        ForeignKey("scan_schedules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    scheduled_for = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    scan_type = Column(
        Enum(
            ScanType,
            values_callable = lambda enum: [item.value for item in enum],
            name = "scan_type",
        ),
        nullable=False,
        default=ScanType.PASSIVE_CTEM,
        index=True,
    )

    #Don't think this is truly needed
    email = Column(String(255))
    verified_domain_id = Column(
        UUID(as_uuid=True),
        ForeignKey("verified_domains.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = Column(
        Enum(
            ScanStatus,
            values_callable=lambda enum: [item.value for item in enum],
            name="scan_status",
        ),
        nullable=False,
        default=ScanStatus.QUEUED,
        index=True,
    )
    progress = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)

    assets = relationship("Asset", back_populates="scan", cascade=CASCADE_ALL)
    findings = relationship("Finding", back_populates="scan", cascade=CASCADE_ALL)
    sources = relationship("ScanSource", back_populates="scan", cascade=CASCADE_ALL)
    report = relationship(
        "Report", back_populates="scan", cascade="all, delete-orphan", uselist=False
    )

    #Remember the back_populates for the other 2
    schedule = relationship("ScanSchedule", back_populates="scans", foreign_keys=[schedule_id])
    user = relationship("User", foreign_keys=[user_id])
    verified_domain = relationship("VerifiedDomain", foreign_keys=[verified_domain_id])
