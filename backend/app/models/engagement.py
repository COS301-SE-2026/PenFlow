import uuid
from datetime import datetime, timezone 

from sqlalchemy import Column, DateTime, Enum, ForeigmKey, String 
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship 

from app.models.base import Base 
from app.schemas.engagement import EngagementStatus 

class Engagement(Base):
    __tablename__ = "engagements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True 
    )

    domain = Column(String(255), nullable=False)

    status = Column(
        Enum(EngagementStatus, name="engagement_status", create_type=False),
        nullable=False,
        default=EngagementStatus.SCHEDULED 
    )

    pentester_name = Column(String(255), nullable=False)

    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    activity_events = relationship(
        "ActivityEvent",
        back_populates="engagement",
        cascade="all, delete-orphan"
    )