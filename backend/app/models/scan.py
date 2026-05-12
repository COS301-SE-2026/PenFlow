#Rough draft of the SQLAlchemy

#from sqlalchemy import Column, String, DateTime, Enum
#from sqlalchemy.dialects.postgresql import UUID
#import uuid
#from datetime import datetime, UTC
#from app.models.base import Base # i'm assuming declarative base setup
#from app.schemas.scan import ScanStatus

#class Scan(Base):
#    __tablename__ = "scans"

#   id = Column(UUID(as_uuid=True))
#   domain = Column(String, index=True,nullable=False)
#   email = Column(String, nullable=True)
#   status = Column(Enum(ScanStatus), default=ScanStatus.PENDING, nullable=False)
#   created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))