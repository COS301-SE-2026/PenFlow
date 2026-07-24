from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.models.verified_domain import DomainVerificationStatus, VerifiedDomain
from app.schemas.domain import DomainSortField, SortOrder


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
    async def create_rec(
        db: AsyncSession, 
        domain: str, 
        verification_token: str, 
        user_id: UUID
    ) -> VerifiedDomain:
        
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
    

    @staticmethod
    def sort_records(query: Select[Any], sort: DomainSortField, order: SortOrder) -> Select[Any]:
        sort_cols: dict[DomainSortField, InstrumentedAttribute[Any]] = {
            DomainSortField.DOMAIN: VerifiedDomain.domain,
            DomainSortField.CREATED_AT: VerifiedDomain.created_at,
            DomainSortField.STATUS: VerifiedDomain.status,
        }

        sort_col = sort_cols[sort]

        if order == SortOrder.ASC:
            return query.order_by(
                sort_col.asc(),
                VerifiedDomain.id.asc(),
            )
        
        return query.order_by(
            sort_col.desc(),
            VerifiedDomain.id.desc(),
        )


    @staticmethod
    async def list_domains(
        db: AsyncSession, 
        user_id: UUID, 
        verification_status: DomainVerificationStatus | None, 
        search: str | None, 
        sort: DomainSortField, 
        order: SortOrder, 
        limit: int, 
        offset: int
    ) -> tuple[list[VerifiedDomain], int]:
        
        query = select(VerifiedDomain).where(
            VerifiedDomain.user_id == user_id,
        )

        count_query = select(func.count(VerifiedDomain.id)
        ).where(VerifiedDomain.user_id == user_id)

        if verification_status is not None:
            query = query.where(
                VerifiedDomain.status == verification_status
            )

            count_query = count_query.where(
                VerifiedDomain.status == verification_status
            )

        stripped_search = search.strip() if search else None

        if stripped_search:
            filter = VerifiedDomain.domain.ilike(f"%{stripped_search}%")
            query = query.where(filter)
            count_query = count_query.where(filter)

        query = DomainRepository.sort_records(
            query,
            sort = sort,
            order = order,
        )
        query = query.limit(limit).offset(offset)

        result = await db.execute(query)
        domains = list(result.scalars().all())

        total = int(await db.scalar(count_query) or 0)

        return domains, total
    

    @staticmethod
    async def get_status_counts(
        db: AsyncSession, 
        user_id: UUID
    ) -> dict[DomainVerificationStatus, int]:
        
        query = (
            select(
                VerifiedDomain.status, 
                func.count(VerifiedDomain.id))
                .where(VerifiedDomain.user_id == user_id)
                .group_by(VerifiedDomain.status)
        )

        result = await db.execute(query)

        counts = {
            DomainVerificationStatus.PENDING: 0,
            DomainVerificationStatus.VERIFIED: 0,
            DomainVerificationStatus.FAILED: 0,
            DomainVerificationStatus.EXPIRED: 0,
        }

        for verification_status, count in result.all():
            counts[verification_status] = int(count)

        return counts
    

    @staticmethod
    async def save_domain(db: AsyncSession, domain_record: VerifiedDomain) -> VerifiedDomain:
        await db.commit()
        await db.refresh(domain_record)

        return domain_record
    

    @staticmethod
    async def delete_domain(db: AsyncSession, domain_record: VerifiedDomain) -> None:
        await db.delete(domain_record)
        await db.commit()