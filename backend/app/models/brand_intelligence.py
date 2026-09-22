import uuid 
import enum 
from datetime import datetime, timezone 

from sqlalchemy import DateTime, Enum, ForeignKey, String, Integer, JSON, UniqueConstraint, Boolean
from sqlalchemy.dialect.postgresql import UUID, JSONB 
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base 

class BrandRiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class BrandCandidateStatus(str, enum.Enum):
    NEW = "new"
    UNDER_REVIEW = "under_review"
    CONFIRMED_IMPERSONATION = "confirmed_impersonation"
    FALSE_POSITIVE = "false_positive"
    RESOLVED = "resolved"

class BrandMonitoring(Base):
    __tablename__ = "brand_monitoring"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    verified_domain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("verified_domain.id", ondelete="CASCADE"),
        nullable=False, 
        unique=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    candidates: Mapped[list["BrandCandidate"]] = relationship(
        "BrandCandidate", back_populates="monitoring", cascade="all, delete-orphan"
    ) 

class BrandCandidate(Base):
    __tablename__ = "brand_candidates"
    __table_args__ = (UniqueConstraint("brand_monitoring_id", "normalized_domain", name="uq_monitor_normalized_domain"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    brand_monitoring_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brand_monitoring.id", ondelete="CASCADE"), 
        nullable=False,
        index=True,
    )

    candidate_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_domain: Mapped[str] = mapped_column(String(255), nullable=False)

    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    risk_level: Mapped[BrandRiskLevel] = mapped_column(
        Enum(
            BrandRiskLevel, 
            values_callable=lambda e: [i.value for i in e],
            name="brand_risk_level",
        ),
        nullable=False, 
        default=BrandRiskLevel.LOW, 
        index=True,
    )

    status: Mapped[BrandCandidateStatus] = mapped_column(
        Enum(
            BrandCandidateStatus,
            value_callable=lambda e: [i.value for i in e],
            name="brand_candidate_status",
        ),
        nullable=False,
        default=BrandCandidateStatus.NEW,
        index=True,
    )

    evidence: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        deault=dict,
    )

    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    monitoring: Mapped["BrandMonitoring"] = relationship(
        "BrandMonitoring", back_populates="candidates"
    )