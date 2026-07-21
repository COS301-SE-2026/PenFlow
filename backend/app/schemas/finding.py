import enum
from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.models.base import Severity

class FindingSortField(str, enum.Enum):
    """
    Fields we will be sorted by
    """
    CREATED_AT = "created_at"
    SEVERITY = "severity"
    SOURCE = "source"
    TITLE = "title"

class SortOrder(str, enum.Enum):
    """
    Order of sort
    """
    ASC = "asc"
    DESC = "desc"

class FindingItem(BaseModel):
    """"
    Each found items blueprint
    """
    id: UUID
    scan_id: UUID
    asset_id: UUID | None = None

    source: str
    severity: Severity
    title: str
    description: str | None = None
    recommendation: str | None = None
    evidence: Any | None = None

    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class FindingCounts(BaseModel):
    """"
    Number for all severity levels"""
    all: int
    info: int
    low: int
    medium: int
    high: int
    critical: int

class FindingPagination(BaseModel):
    """
    Pagination from domain setup
    """
    total: int
    limit: int
    offset: int
    has_more: bool

class FindingList(BaseModel):
    items: list[FindingItem]
    counts: FindingCounts
    pagination: FindingPagination