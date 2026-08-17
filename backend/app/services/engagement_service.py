from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.engagement import Engagement
from app.models.user import User
from app.repositories.engagement_repository import EngagementRepository
from app.schemas.engagement import (
    EngagementCreateRequest,
    EngagementCreateResponse,
    EngagementRequestAssetResponse,
    EngagementRequestDetailResponse,
)


class EngagementService:
    @staticmethod
    def build_create_response\
        (
            engagement: Engagement,
            asset_count: int,
        ) -> EngagementCreateResponse:
        #confirmation of request for ui
        return EngagementCreateResponse\
        (
            id=engagement.id,
            status=engagement.status,
            engagement_type=engagement.engagement_type,
            objective=engagement.objective or engagement.scope,
            start_date=engagement.requested_start_date,
            end_date=engagement.requested_end_date,
            asset_count=asset_count,
            assigned_pentester_id=engagement.assigned_to,
            created_at=engagement.created_at,
        )

    @staticmethod
    async def create_engagement\
    (
        db: AsyncSession,
        request: EngagementCreateRequest,
        client_user_id: UUID,
    ) -> EngagementCreateResponse:
        # save the request first.
        engagement = await EngagementRepository.create_engagement\
        (
            db,
            request=request,
            client_user_id=client_user_id,
        )
        return EngagementService.build_create_response\
        (
            engagement,
            asset_count=len(request.assets),
        )

    @staticmethod
    async def get_engagement\
    (
        db: AsyncSession,
        engagement_id: UUID,
        user_id: UUID,
    ) -> EngagementRequestDetailResponse:
        user = await db.get(User, user_id)

        if user is None:
            raise HTTPException\
            (
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not present",
            )

        #The declared scope for the request.
        #assets the client is giving permission to test
        if user.role in {"admin", "pentester"}:
            engagement = await EngagementRepository.get_id\
            (
                db,
                engagement_id=engagement_id,
            )
        else:
            engagement = await EngagementRepository.get_id_client\
            (
                db,
                engagement_id=engagement_id,
                client_user_id=user_id,
            )

        if engagement is None:
            raise HTTPException\
            (
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Engagement request was not found",
            )

        return EngagementRequestDetailResponse(
            id=engagement.id,
            status=engagement.status,
            engagement_type=engagement.engagement_type,
            objective=engagement.objective or engagement.scope,
            start_date=engagement.requested_start_date,
            end_date=engagement.requested_end_date,
            constraints=engagement.constraints,
            primary_contact=engagement.primary_contact,
            assets=[
                EngagementRequestAssetResponse(
                    id=asset.id,
                    type=asset.asset_type,
                    value=asset.identifier,
                )
                for asset in engagement.assets
            ],
            assigned_pentester_id=engagement.assigned_to,
            created_at=engagement.created_at,
        )