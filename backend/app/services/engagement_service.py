from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.engagement import Engagement
from app.models.user import User # type: ignore[attr-defined]
from app.repositories.engagement_repository import EngagementRepository
from app.schemas.engagement import \
(
    EngagementCreateRequest,
    EngagementCreateResponse,
    EngagementDetailResponse,
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
            objective=engagement.objective,
            start_date=engagement.start_date,
            end_date=engagement.end_date,
            asset_count=asset_count,
            assigned_pentester_id=engagement.assigned_pentester_id,
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
    ) -> EngagementDetailResponse:
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

        return EngagementDetailResponse.model_validate(engagement)