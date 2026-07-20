import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DomainVerificationStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"

class DomainVerificationCode(str, enum.Enum):
    VERIFIED = "verified"
    RECORD_NOT_FOUND = "record_not_found"
    TOKEN_MISMATCH = "token_mismatch"
    LOOKUP_FAILED = "lookup_failed"

class VerifiedDomain(Base):
    __tablename__ = "verified_domains"
    __table_args__ = (
        UniqueConstraint("user_id", "domain", name="uq_org_domain"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
    )

    organisation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), 
        #ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=True,
        #index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    domain: Mapped[str] = mapped_column(
        String(255), 
        nullable=False, 
        index=True,
    )


    status: Mapped[DomainVerificationStatus] = mapped_column(
        Enum(
            DomainVerificationStatus,
            values_callable=lambda e: [i.value for i in e],
            name="domain_verification_status"
        ),
        nullable=False,
        default=DomainVerificationStatus.PENDING,
        index=True,
    )

    verification_method: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        default="dns_txt",
    )
    
    verification_token: Mapped[str] = mapped_column(
        Text, 
        nullable=False,
    )

    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
    )

    last_verification_code: Mapped[DomainVerificationCode | None] = mapped_column(
        Enum(
            DomainVerificationCode, 
            values_callable=lambda e: [i.value for i in e],
            name="domain_verification_code",
        ),
        nullable=True,
    )