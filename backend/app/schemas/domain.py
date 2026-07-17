import enum
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from app.models.verified_domain import DomainVerificationStatus, DomainVerificationCode

class AddDomainRequest(BaseModel):
    domain: str = Field(..., min_length = 1, max_length = 255, description="The domain to verify")

class VerifiedDomainResponse(BaseModel):
    id: UUID
    domain: str
    status: DomainVerificationStatus
    verification_token: str
    verified_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class DomainSortField(str, enum.Enum):
    DOMAIN = "domain"
    CREATED_AT = "created_at"
    STATUS = "status"

class SortOrder (str, enum.Enum):
    ASC = "asc"
    DESC = "desc"

class DomainItem(BaseModel):
    id: UUID
    domain: str
    status: DomainVerificationStatus
    verification_method: str
    verification_token: str
    created_at: datetime
    verified_at: datetime | None = None
    last_checked_at: datetime | None = None
    last_verification_code: DomainVerificationCode | None = None

    model_config = ConfigDict(from_attributes=True)

class DomainCounts(BaseModel):
    all: int
    pending: int
    verified: int
    failed: int
    expired: int


class DomainPagination(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool


class DomainList(BaseModel):
    items: list[DomainItem]
    counts: DomainCounts
    pagination: DomainPagination