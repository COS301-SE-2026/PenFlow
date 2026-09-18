from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import RetestStatus
from app.models.finding import Finding
from app.models.finding_retest import FindingRetest
from app.schemas.retest import RetestUpdate

OPEN_RETEST_STATUSES = (RetestStatus.REQUESTED, RetestStatus.IN_PROGRESS)   

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

    @staticmethod
    async def list_eligible_findings(
        db: AsyncSession,
        engagement_id: UUID,
    ) -> list[Finding]:
        disqualifying_finding_ids = select(FindingRetest.finding_id).where(
            FindingRetest.status.in_(
                (RetestStatus.REQUESTED, RetestStatus.IN_PROGRESS, RetestStatus.RESOLVED)
            )
        )

        query =select(Finding).where(
            Finding.engagement_id == engagement_id,
            Finding.id.notin_(disqualifying_finding_ids),
        )

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create_many(
        db: AsyncSession,
        finding_ids: list[UUID],
        requested_by: UUID,
    ) -> list[FindingRetest]:
        retests = [
            FindingRetest(finding_id=finding_id, requested_by=requested_by)
            for finding_id in finding_ids
        ]

        db.add_all(retests)
        await db.commit()

        for retest in retests:
            await db.refresh(retest, attribute_names=["finding"])

        return retests


    #order by findings id , then newest finding per finding then 
    # distinct keep the latest findings
    @staticmethod
    async def list_latest_by_engagement(
        db: AsyncSession,
        engagement_id: UUID,
    ) -> list[tuple[Finding, FindingRetest | None]]:
        query = (
            select(Finding, FindingRetest)
            .outerjoin(
                FindingRetest,
                FindingRetest.finding_id == Finding.id,
            )
            .where(
                Finding.engagement_id == engagement_id,
            )
            .distinct(Finding.id)
            .order_by(Finding.id, FindingRetest.requested_at.desc())
        )

        result = await db.execute(query)
        return [(finding, retest) for finding, retest in result.all()]

    @staticmethod
    async def count_open_by_engagement(
        db: AsyncSession,
        engagement_id: UUID,
    ) -> int:
        query = (
            select(func.count(FindingRetest.id))
            .join(Finding, Finding.id == FindingRetest.finding_id)
            .where(
                Finding.engagement_id == engagement_id,
                FindingRetest.status.in_(OPEN_RETEST_STATUSES),
            )
        )

        result = await db.execute(query)
        return int(result.scalar_one())

    