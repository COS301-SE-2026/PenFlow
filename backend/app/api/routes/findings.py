from typing import Annotated, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.middleware.auth import get_current_user
from app.models.base import Severity
from app.repositories.user_repo import get_user_id_by_provider_id
from app.schemas.domain import SortOrder
from app.schemas.finding import \
(
    FindingList,
    FindingSortField,
)
from app.services.finding_service import FindingService
from app.utils.db import get_db

#mostly a carbon copy of domains route
router = APIRouter\
(
    prefix="/findings",
    tags=["Findings"],
)


@router.get("", response_model=FindingList)
async def get_findings\
(
    scan_id: UUID,
    severity: Annotated[Severity | None, Query(alias="severity")] = None,
    search: Annotated[str | None, Query(max_length=255)] = None,
    sort: FindingSortField = FindingSortField.CREATED_AT,
    order: SortOrder = SortOrder.DESC,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> FindingList:

    #Get the currently authenticated user's database id
    user_id = await get_user_id_by_provider_id\
    (
        db,
        current_user["sub"],
    )

    #If the user does not exist we stop
    if user_id is None:
        raise HTTPException\
        (
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not present.",
        )

    #Retrieve the requested findings for the service component
    return await FindingService.list_findings\
    (
        db=db,
        #user_id=user_id, will add this if we need to validate
        scan_id=scan_id,
        severity=severity,
        search=search,
        sort=sort,
        order=order,
        limit=limit,
        offset=offset,
    )