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

class FindingStatus(str, enum.Enum):
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    RESOLVED = 'resolved'
    ACCEPTED_RISK = 'accepted_risk'
    FALSE_POSITIVE = 'false_positive'