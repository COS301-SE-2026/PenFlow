import uuid
from datetime import datetime, timezone 

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text 
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base 
from app.schemas.engagement import ActivityBadge 

class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    engagement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    timestamp = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    description = Column(Text, nullable=False)

    badge = Column(
        Enum(ActivityBadge, name="activity_badge", create_type=False)
    )

    subtext = Column(String(255))

    engagement = relationship("Engagement", back_populates="activity_events")