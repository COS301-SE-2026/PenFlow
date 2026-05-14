from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, UTC
import enum

class Base(DeclarativeBase):
    pass

class ScanStatus(str, enum.Enum):
    QUEUED = 'queued'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    PARTIAL = 'partial'

class Severity(str,enum.Enum):
    INFO = 'info'
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'