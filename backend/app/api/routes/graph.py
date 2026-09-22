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
    db: DbSession,  
    user: CurrentUser,
) -> Scan:
    return await GraphService.require_scan_access(db, scan_id, user)

ScanAccess = Annotated[Scan, Depends(_scan_access)]

@router.get(
    "/{scan_id}/graph",
    response_model=GraphResponse,
    summary="Get the vulnerability graph for a scan",
)

async def get_scan_graph(scan: ScanAccess, db: DbSession) -> GraphResponse:
    return await GraphService.get_graph(db, scan)

@router.get(
    "/{scan_id}/graph/summary",
    response_model=GraphSummaryResponse,
    summary= "Get vulnerability graph statistics for a scan",
)
async def get_scan_graph_summary(scan: ScanAccess, db: DbSession) -> GraphSummaryResponse:
    return await GraphService.get_summary(db, scan)

@router.get(
    "/{scan_id}/graph/nodes/{node_id}",
    response_model= GraphNodeDetailResponse,
    summary= "Get detail for a single vulnerability graph node",
)
async def get_scan_graph_node(
    scan: ScanAccess,
    db: DbSession,
    node_id: str,
) -> GraphNodeDetailResponse:
    return await GraphService.get_node(db, scan, node_id)

@router.get(
    "/{scan_id}/graph/paths",
    response_model=GraphPathsResponse,
    summary= "Get risk/exposure paths through the vulnerability graph",
)
async def get_scan_graph_paths(
    scan: ScanAccess,
    db: DbSession,
    severity: Literal["high", "critical"] | None = Query(None),
    finding_id: UUID | None = Query(None),   
    asset_id: UUID | None = Query(None),
    limit: int = Query(10, ge=1, le=100),
) -> GraphPathsResponse:
    return await GraphService.get_paths(
    db,
    scan,
    severity=severity,
    finding_id=finding_id,
    asset_id=asset_id,
    limit=limit,
)

@router.get(
    "/{scan_id}/graph/nodes/{node_id}/neighborhood",
    response_model=GraphNeighborhoodResponse,
    summary="Get the subgraph around a single node",
)
async def get_scan_graph_node_neighborhood(
    scan: ScanAccess,
    db: DbSession,
    node_id: str,
    depth: int = Query(2, ge=1, le=3),
) -> GraphNeighborhoodResponse:
    return await GraphService.get_neighborhood(db, scan, node_id, depth=depth)

@router.get(
    "/{scan_id}/graph/compare/{previous_scan_id}",
    response_model = GraphCompareResponse,
    summary="Compare the vulnerability graph of two scans",
)
async def get_scan_graph_compare(
    scan: ScanAccess,
    db: DbSession,
    user: CurrentUser,
    previous_scan_id: UUID,
) -> GraphCompareResponse:
    previous_scan = await GraphService.require_scan_access(db, previous_scan_id, user)
    return await GraphService.compare_scans(db, scan, previous_scan)

