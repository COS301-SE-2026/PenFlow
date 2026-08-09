from pydantic import BaseModel
from typing import List
from datetime import datetime
class EngagementMetric(BaseModel):
    active_users: int
    total_views: int
    interaction_rate: float
    timestamp: datetime