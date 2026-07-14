from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AddDomainRequest(BaseModel):
    domain: str = Field(..., description="The domain to verify")

class VerifiedDomainResponse(BaseModel):
    id: UUID
    domain: str
    status: str
    verification_token: str
    verified_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)