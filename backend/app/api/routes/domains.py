from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

#from app.api.middleware.auth import get_current_user
from app.models.verified_domain import DomainVerificationStatus, VerifiedDomain
from app.schemas.domain import AddDomainRequest, VerifiedDomainResponse
from app.services.verification_service import VerificationService
from app.utils.db import get_db

router =  APIRouter(prefix="/domains", tags=["Domain Verification"])

@router.post("/", response_model=VerifiedDomainResponse, status_code=status.HTTP_201_CREATED)
async def add_domain_for_verification(
    request: AddDomainRequest,
    db: AsyncSession = Depends(get_db),
    #current_user = Depends(get_current_user)
) -> Any:
   #Generate token
   token = VerificationService.generate_txt_token()

   #save db
   new_domain = VerifiedDomain(
        domain=request.domain,
        verification_token=token,
        status=DomainVerificationStatus.PENDING,
        #organisation_id=current_user.get("org_id")
   )

   db.add(new_domain)
   await db.commit()
   await db.refresh(new_domain)

   return new_domain

@router.post(
    "/{domain_id}/verify",
    response_model=VerifiedDomainResponse,
    status_code=status.HTTP_200_OK)
async def verify_domain_ownership(
    domain_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:
    query = select(VerifiedDomain).where(VerifiedDomain.id == domain_id)
    result = await db.execute(query)
    domain_record = result.scalar_one_or_none()

    if not domain_record:
        raise HTTPException(status_code=404, detail="Domain tracking record not found.")

    if domain_record.status == DomainVerificationStatus.VERIFIED:
        return domain_record

    is_verified = VerificationService.verify_dns_txt(
        domain=str(domain_record.domain),
        expected_token=str(domain_record.verification_token)
    )

    if is_verified:
        domain_record.status = DomainVerificationStatus.VERIFIED
        domain_record.verified_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(domain_record)
        return domain_record
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification failed. Ensure the TXT record is added and has propagated."
        )


