from datetime import date
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class AdminPagination(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool


class AdminUserListItem(BaseModel):
    id: UUID
    full_name: str | None = None
    email: str | None = None
    role: str | None = None
    joined_date: date | None = None
    active_engagements: int


class AdminUserListResponse(BaseModel):
    items: list[AdminUserListItem]
    pagination: AdminPagination

class AdminUserRoleFilter(str, Enum):
    ADMIN = "admin"
    CLIENT = "client"
    PENTESTER = "pentester"