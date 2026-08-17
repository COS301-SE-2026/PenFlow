from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import EngagementStatus
from app.models.engagement import Engagement
from app.models.engagement_asset import EngagementAsset
from app.schemas.engagement import EngagementCreateRequest


#the engagement is the main ticket
#assets are subsequent rows
class EngagementRepository:
    @staticmethod
    async def create_engagement\
    (
        db: AsyncSession,
        request: EngagementCreateRequest,
        client_user_id: UUID,
    ) -> Engagement:
        objective = request.objective.strip()
        engagement = Engagement\
        (
            requested_by=client_user_id,
            assigned_to=None,
            engagement_type=request.engagement_type,
            priority="medium",
            status=EngagementStatus.SCOPING,
            title=objective[:255],
            scope=objective,
            objective=objective,
            estimated_quote=Decimal("0.00"),
            estimated_duration_days=None,
            requested_start_date=request.start_date,
            requested_end_date=request.end_date,
            constraints=request.constraints.strip() if request.constraints else None,
            primary_contact=request.primary_contact.strip() if request.primary_contact else None,
        )

        engagement.assets = \
        [
            EngagementAsset\
            (
                identifier=asset.value.strip(),
                asset_type=asset.type.value,
                asset_metadata={},
            )
            for asset in request.assets
        ]

        db.add(engagement)
        await db.commit()
        await db.refresh(engagement)

        return engagement

    #admin/pentester path, fetch by id only
    @staticmethod
    async def get_id\
    (
        db: AsyncSession,
        engagement_id: UUID,
    ) -> Engagement | None:
        query = \
        (
            select(Engagement)
            .options(selectinload(Engagement.assets))
            .where(Engagement.id == engagement_id)
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    #client path, fetch by id and the owner
    @staticmethod
    async def get_id_client\
    (
        db: AsyncSession,
        engagement_id: UUID,
        client_user_id: UUID,
    ) -> Engagement | None:
        query = \
        (
            select(Engagement)
            .options(selectinload(Engagement.assets))
            .where(
                Engagement.id == engagement_id,
                Engagement.requested_by == client_user_id,
            )
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()