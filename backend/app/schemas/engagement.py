from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class EngagementStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"

class ActivityBadge(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    CRITICAL = "CRITICAL"
    INFO = "INFO"

class ActivityEventRead(BaseModel):
    id: str
    engagement_id: str
    timestamp: datetime
    description: str
    badge: Optional[ActivityBadge] = None
    subtext: Optional[str] = None 

class EngagementHistoryResponse(BaseModel):
    metrics: List[EngagementMetric]