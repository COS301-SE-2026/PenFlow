from typing import Any, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_user
from app.models.verified_domain import DomainVerificationStatus
from app.schemas.domain import AddDomainRequest, VerifiedDomainResponse, DomainList, DomainSortField, SortOrder
from app.services.domain_service import DomainService
from app.repositories.user_repo import get_user_id_by_provider_id
from app.utils.db import get_db


router =  APIRouter(prefix="/domains", tags=["Domain Verification"])

@router.post("/", response_model=VerifiedDomainResponse, status_code=status.HTTP_201_CREATED)
async def add_domain_for_verification(
    request: AddDomainRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> Any:

    user_id = await get_user_id_by_provider_id(
        db,
        current_user["sub"],
    )
    
    if user_id is None:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "User not present.",
        )
    
    return await DomainService.add_domain(
        db,
        domain = request.domain,
        user_id = user_id,
    )


@router.post("/{domain_id}/verify", response_model=VerifiedDomainResponse, status_code=status.HTTP_200_OK)
async def verify_domain_ownership(
    domain_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> Any:
    
    user_id = await get_user_id_by_provider_id(
        db,
        current_user["sub"],
    )
    
    if user_id is None:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "User not present.",
        )
    
    return await DomainService.verify_domain(
        db,
        domain_id = domain_id,
        user_id = user_id,
    )


@router.get("", response_model=DomainList)
async def get_domains(
    verification_status: Annotated[DomainVerificationStatus | None, Query(alias="status")] = None, 
    search: Annotated[str | None, Query(max_length=255)] = None,
    sort: DomainSortField = DomainSortField.CREATED_AT,
    order: SortOrder = SortOrder.DESC,
    limit: Annotated[int, Query(ge=1, le=100)] = 20, 
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> DomainList:
    
    user_id = await get_user_id_by_provider_id(
        db,
        current_user["sub"],
    )
    
    if user_id is None:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "User not present.",
        )
    
    return await DomainService.list_domains(
        db,
        user_id = user_id,
        verification_status = verification_status,
        search = search,
        sort = sort,
        order = order,
        limit = limit,
        offset = offset,
    )
