from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.verified_domain import VerifiedDomain

from app.repositories.domain_repository import DomainRepository

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
                status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail = "A valid domain is needed",
            )
        
        return stripped
    

    @staticmethod
    async def add_domain(db: AsyncSession, domain: str, user_id: UUID) -> VerifiedDomain:
        stripped_domain = DomainService.strip_domain(domain)

        existing_domain = await DomainRepository.get_by_domain(
            db,
            domain = stripped_domain,
            user_id = user_id,
        )

        if existing_domain is not None:
            raise HTTPException(
                status_code = status.HTTP_409_CONFLICT,
                detail = "This domain has already been added",
            )
        
        token = VerificationService.generate_txt_token()

        return await DomainRepository.create_rec(
            db,
            domain = stripped_domain,
            verification_token = token,
            user_id = user_id,
        )