#Rough draft of the SQLAlchemy

from sqlalchemy import Column, String, Integer, DateTime, Text, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, UTC
from app.models.base import Base 
from app.models.base import Base, ScanStatus

class Scan(Base):
    __tablename__ = "scans"

   id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
   #I'm going to ommit organisation_id and user_id for now until auth
   domain = Column(String(255),nullable=False, index=True)
   email = Column(String(255))
   status = Column(Enum(ScanStatus), nullable=False, default=ScanStatus.QUEUED, index=True)
   progress = Column(Integer, nullable=False, default=0)
   created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
   started_at = Column(DateTime(timezone=True))
   completed_at = Column(DateTime(timezone=True))
   error_message = Column(Text)

   assets = relationship("Asset", back_populates="scan", cascade="all, delete-orphan")
   findings = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")
   sources = relationship("ScanSource", back_populates="scan", cascade="all, delete-orphan")
