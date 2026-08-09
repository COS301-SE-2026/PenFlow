from app.repositories.engagement_repo import EngagementRepository

class EngagementService:
    def __init__(self, repo: EngagementRepository):
        self.repo = repo

    async def get_dashboard_summary(self):
        return await self.repo.get_aggregated_metrics()

    async def get_historical_data(self, time_range: str):
        return await self.repo.get_time_series(time_range = time_rnage)