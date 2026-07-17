from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.verified_domain import DomainVerificationStatus, VerifiedDomain


class DomainRepository:

    @staticmethod
    async def get_by_id(db: AsyncSession, domain_id: UUID, user_id: UUID) -> VerifiedDomain | None:
        query = select(VerifiedDomain).where(
            VerifiedDomain.id == domain_id,
            VerifiedDomain.user_id == user_id,
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()
    

    @staticmethod
    async def get_by_domain(db: AsyncSession, domain: str, user_id: UUID) -> VerifiedDomain | None:
        query = select(VerifiedDomain).where(
            VerifiedDomain.user_id == user_id,
            func.lower(VerifiedDomain.domain) == domain.lower(),
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()
    

    @staticmethod
    async def create_rec(db: AsyncSession, domain: str, verification_token: str, user_id: UUID) -> VerifiedDomain:
        domain_rec = VerifiedDomain(
            domain = domain,
            user_id = user_id,
            verification_token = verification_token,
            status = DomainVerificationStatus.PENDING
        )

        db.add(domain_rec)
        await db.commit()
        await db.refresh(domain_rec)

        return domain_rec