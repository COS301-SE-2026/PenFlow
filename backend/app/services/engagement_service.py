from typing import List
from app.schemas.engagement import EngagementRead, ActivityEventRead


class EngagementService:
    def __init__(self, repo):
        self.repo = repo

    async def get_all_engagements(self) -> List[EngagementRead]:
        """
        Fetch all engagements.
        """
        return await self.repo.get_all()
        pass

    async def get_engagement_activity(self, engagement_id: str) -> List[ActivityEventRead]:
        """
        Fetch the chronological event log.
        """
        pass