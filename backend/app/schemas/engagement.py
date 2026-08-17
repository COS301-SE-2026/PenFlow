from datetime import date, datetime
from ipaddress import ip_address
from typing import Self
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.base import EngagementAssetType, EngagementStatus, EngagementType


#one asset row from the asset declaration section of the form
class EngagementAssetCreate(BaseModel):
    type: EngagementAssetType
    value: str = Field(..., min_length=1, max_length=2048)

    #backend val matters cause it will define our asset scope
    @model_validator(mode="after")
    def validate_asset_value(self) -> Self:
        stripped_value = self.value.strip()

        if not stripped_value:
            raise ValueError("Asset value cannot be empty.")

        if self.type == EngagementAssetType.IP:
            try:
                ip_address(stripped_value)
            except ValueError as error:
                raise ValueError("Asset value must be a valid IP address.") from error

        if self.type == EngagementAssetType.URL and not \
        (
            stripped_value.startswith("http://") or stripped_value.startswith("https://")
        ):
            raise ValueError("URL assets must start with http:// or https://.")

        if self.type in \
        {
            EngagementAssetType.DOMAIN,
            EngagementAssetType.HOSTNAME,
        }:
            if "/" in stripped_value or " " in stripped_value:
                raise ValueError("Domain and hostname assets cannot contain spaces or paths.")

        self.value = stripped_value
        return self


#Matching the Phase 3 engagement form
#It creates a scoping ticket, WE DO NOT RUN SCAN HERE
class EngagementCreateRequest(BaseModel):
    engagement_type: EngagementType
    objective: str = Field(..., min_length=1, max_length=5000)
    start_date: date | None = None
    end_date: date | None = None
    constraints: str | None = Field(default=None, max_length=5000)
    primary_contact: str | None = Field(default=None, max_length=255)
    assets: list[EngagementAssetCreate] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_date_range(self) -> Self:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date cannot be after end_date.")

        return self


class EngagementCreateResponse(BaseModel):
    id: UUID
    status: EngagementStatus
    engagement_type: EngagementType
    objective: str
    start_date: date | None = None
    end_date: date | None = None
    asset_count: int
    assigned_pentester_id: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EngagementAssetResponse(BaseModel):
    id: UUID
    type: EngagementAssetType
    value: str

    model_config = ConfigDict(from_attributes=True)


class EngagementDetailResponse(BaseModel):
    id: UUID
    status: EngagementStatus
    engagement_type: EngagementType
    objective: str
    start_date: date | None = None
    end_date: date | None = None
    constraints: str | None = None
    primary_contact: str | None = None
    assets: list[EngagementAssetResponse]
    assigned_pentester_id: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)