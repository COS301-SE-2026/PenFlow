import enum

from sqlalchemy.orm import DeclarativeBase


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