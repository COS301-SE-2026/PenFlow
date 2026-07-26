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

class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"

class ScanSourceStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"

class DomainVerificationStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"

class DomainVerificationCode(str, enum.Enum):
    VERIFIED = "verified"
    RECORD_NOT_FOUND = "record_not_found"
    TOKEN_MISMATCH = "token_mismatch"
    LOOKUP_FAILED = "lookup_failed"

class ScanType(str, enum.Enum):
    PASSIVE_CTEM = "passive_ctem"
    ACTIVE_VULNERABILITY = "active_vulnerability"

class ScanScheduleFrequency(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
class FindingStatus(str, enum.Enum):
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    RESOLVED = 'resolved'
    ACCEPTED_RISK = 'accepted_risk'
    FALSE_POSITIVE = 'false_positive'
