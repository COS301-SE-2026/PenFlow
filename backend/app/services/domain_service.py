from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import (
    DomainVerificationCode,
    DomainVerificationStatus,
)
from app.models.verified_domain import VerifiedDomain
from app.repositories.domain_repository import DomainRepository
from app.schemas.domain import (
    DomainCounts,
    DomainItem,
    DomainList,
    DomainPagination,
    DomainSortField,
    SortOrder,
)
from app.services.verification_service import VerificationService


class DomainService:
    @staticmethod
    def strip_domain(domain: str) -> str:
        stripped = domain.strip().lower()

        if stripped.startswith("https://"):
            stripped = stripped.removeprefix("https://")

        elif stripped.startswith("http://"):
            stripped = stripped.removeprefix("http://")

        stripped = stripped.split("/", maxsplit=1)[0]
        stripped = stripped.rstrip(".")

        if not stripped:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A valid domain is needed",
            )

        return stripped

    @staticmethod
    async def add_domain(db: AsyncSession, domain: str, user_id: UUID) -> VerifiedDomain:
        stripped_domain = DomainService.strip_domain(domain)

        existing_domain = await DomainRepository.get_by_domain(
            db,
            domain=stripped_domain,
            user_id=user_id,
        )

        if existing_domain is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This domain has already been added",
            )

        token = VerificationService.generate_txt_token()

        return await DomainRepository.create_rec(
            db,
            domain=stripped_domain,
            verification_token=token,
            user_id=user_id,
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
        offset: int,
    ) -> DomainList:

        domains, total = await DomainRepository.list_domains(
            db,
            user_id=user_id,
            verification_status=verification_status,
            search=search,
            sort=sort,
            order=order,
            limit=limit,
            offset=offset,
        )

        status_counts = await DomainRepository.get_status_counts(
            db,
            user_id=user_id,
        )

        items = [DomainItem.model_validate(domain) for domain in domains]

        return DomainList(
            items=items,
            counts=DomainCounts(
                all=sum(status_counts.values()),
                pending=status_counts[DomainVerificationStatus.PENDING],
                verified=status_counts[DomainVerificationStatus.VERIFIED],
                failed=status_counts[DomainVerificationStatus.FAILED],
                expired=status_counts[DomainVerificationStatus.EXPIRED],
            ),
            pagination=DomainPagination(
                total=total,
                limit=limit,
                offset=offset,
                has_more=offset + len(items) < total,
            ),
        )

    @staticmethod
    async def verify_domain(db: AsyncSession, domain_id: UUID, user_id: UUID) -> VerifiedDomain:

        domain_rec = await DomainRepository.get_by_id(
            db,
            domain_id=domain_id,
            user_id=user_id,
        )

        if domain_rec is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Domain record was not found",
            )

        if domain_rec.status == DomainVerificationStatus.VERIFIED:
            return domain_rec

        current_code = await VerificationService.verify_dns_txt(
            str(domain_rec.domain),
            str(domain_rec.verification_token),
        )

        domain_rec.last_checked_at = datetime.now(timezone.utc)
        domain_rec.last_verification_code = current_code

        if current_code == DomainVerificationCode.VERIFIED:
            domain_rec.status = DomainVerificationStatus.VERIFIED
            domain_rec.verified_at = datetime.now(timezone.utc)
            domain_rec.expires_at = None

            return await DomainRepository.save_domain(
                db,
                domain_rec,
            )

        domain_rec.status = DomainVerificationStatus.PENDING

        await DomainRepository.save_domain(
            db,
            domain_rec,
        )

        errors = {
            DomainVerificationCode.RECORD_NOT_FOUND: (
                "The verification TXT record could not be found."
            ),
            DomainVerificationCode.TOKEN_MISMATCH: (
                "A TXT record was found, but the verification token "
                "did not match."
            ),
            DomainVerificationCode.LOOKUP_FAILED: (
                "The DNS lookup could not be completed. Please try "
                "again later."
            ),
        }

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=errors[current_code],
        )

    @staticmethod
    async def delete_domain(db: AsyncSession, domain_id: UUID, user_id: UUID) -> None:

        domain_rec = await DomainRepository.get_by_id(
            db,
            domain_id=domain_id,
            user_id=user_id,
        )

        if domain_rec is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Domain record was not found",
            )

        await DomainRepository.delete_domain(
            db,
            domain_rec,
        )
