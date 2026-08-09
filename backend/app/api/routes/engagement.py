from fastapi import APIRouter, Depends
from app.schemas.engagement import EngagementMetric, EngagementHistoryResponse
from app.services.engagement_service import EngagementService

router = APIRouter()

@router.get("/summary", response_model=EngagementMetric)
async def get_engagement_summary(
    service: EngagementService = Depends(get_engagement_service)
):
    """
    Fetch the internal state of the live dashboard.
    """
    return await service.get_dashboard_summary()

@router.get("/history", response_model=EngagementHistoryResponse)
async def get_engagement_history(
    time_range: str = "24h",
    service: EngagementService = Depends(get_engagement_service)
):
    """
    Fetch historical data for dashboard charts.
    """
    return await service.get_historical_data(time_range)
