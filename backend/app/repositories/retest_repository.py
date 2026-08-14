from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.finding import Finding
from app.models.finding_retest import FindingRetest
from app.schemas.retest import RetestUpdate


class RetestRepository:
    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        retest_id: UUID,
    ) -> FindingRetest | None:
        query = (
            select(FindingRetest).options(
                selectinload(FindingRetest.finding)
            ).where(
                FindingRetest.id == retest_id
            )
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()


    @staticmethod
    async def list_by_engagement(
        db: AsyncSession,
        engagement_id: UUID,
    ) -> list[FindingRetest]:
        query = (
            select(FindingRetest).join(
                Finding, Finding.id == FindingRetest.finding_id
            ).options(
                selectinload(FindingRetest.finding)
            ).where(
                Finding.engagement_id == engagement_id
            ).order_by(
                FindingRetest.requested_at.desc(),
                FindingRetest.id.desc(),
            )
        )

        result = await db.execute(query)
        return list(result.scalars().all())


    @staticmethod 
    async def update_retest(
        db: AsyncSession,
        retest: FindingRetest,
        request: RetestUpdate,
    ) -> FindingRetest:
        updates = request.model_dump(exclude_unset=True)

        for field, value in updates.items():
            setattr(retest, field, value)

        await db.commit()
        await db.refresh(retest)

        return retest