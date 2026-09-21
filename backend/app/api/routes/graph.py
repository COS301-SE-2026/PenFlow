from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import require_user
from app.models.scan import Scan
from app.models.user import User
from app.schemas.graph import (
    GraphCompareResponse,
    GraphNeighborhoodResponse,
    GraphNodeDetailResponse,
    GraphPathsResponse,
    GraphResponse,
    GraphSummaryResponse,
)
from app.services.graph_service import GraphService
from app.utils.db import get_db

router = APIRouter(prefix="/scans", tags=["Graph"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(require_user)]

async def _scan_access(
    scan_id: UUID,
    db, DbSession,  
    user: CurrentUser,
) -> Scan:
    return await GraphService.require_scan_access(db, scan_id, user)

ScanAccess = Annotated[Scan, Depends(_scan_access)]

@router.get(
    "/{scan_id}/graph",
    response_model=GraphResponse,
    summary="Get the vulnerability graph for a scan",
)