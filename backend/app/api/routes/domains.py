from typing import Any
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_user
from app.models.verified_domain import VerifiedDomain, DomainVerificationStatus
from app.schemas.domain import AddDomainRequest, VerifiedDomainResponse
from app.services.verification_service import VerificationService
from app.utils.db import get_db

router =  APIRouter(prefix="/domains", tags=["Domain Verification"])

@router.post("/", response_model=VerifiedDomainResponse, status_code=status.HTTP_201_CREATED)
async def add_domain_for_verification(
    request: AddDomainRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
) -> Any:
   #Generate token
   token = VerificationService.generate_txt_token()

   #save db
   new_domain = VerifiedDomain(
        domain=request.domain,
        verification_token=token,
        status=DomainVerificationStatus.PENDING,
        organisation_id=current_user.get("org_id")
   )

   db.add(new_domain)
   await db.commit()
   await db.refresh(new_domain)

   return new_domain


