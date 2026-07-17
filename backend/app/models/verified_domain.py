import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

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
        UniqueConstraint("organisation_id", "domain", name="uq_org_domain"),
    )

    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
    )

    organisation_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    domain = Column(
        String(255), 
        nullable=False, 
        index=True,
    )


    status = Column(
        Enum(
            DomainVerificationStatus,
            values_callable=lambda e: [i.value for i in e],
            name="domain_verification_status"
        ),
        nullable=False,
        default=DomainVerificationStatus.PENDING,
        index=True,
    )

    verification_method = Column(
        String(50), 
        nullable=False, 
        default="dns_txt",
    )
    
    verification_token = Column(
        Text, 
        nullable=False,
    )

    verified_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    last_checked_at = Column(
        DateTime(timezone=True), 
        nullable=True,
    )

    last_verification_code = Column(
        Enum(
            DomainVerificationCode, 
            values_callable=lambda e: [i.value for i in e],
            name="domain_verification_code",
        ),
        nullable=True,
    )