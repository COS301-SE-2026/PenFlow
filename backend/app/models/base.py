import enum

from sqlalchemy.orm import DeclarativeBase
from enum import Enum

class Base(DeclarativeBase):
    pass


class ScanStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class Severity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


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
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ACCEPTED_RISK = "accepted_risk"
    FALSE_POSITIVE = "false_positive"

#Engagement type from form
class EngagementType(str, enum.Enum):
    BLACK_BOX = "black_box"
    GREY_BOX = "grey_box"
    WHITE_BOX = "white_box"

#initial set up for our engagement survey
class EngagementStatus(str, enum.Enum):
    REQUESTED = "requested"
    SCOPING = "scoping"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class RetestStatus(str, enum.Enum):
    REQUESTED = "requested"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    STILL_VULNERABLE = "still_vulnerable"

class UserRole(str, enum.Enum):
    CLIENT = "client"
    PENTESTER  = "pentester"
    SERVICE_DELIVERY = "service_delivery"
    ADMIN = "admin"

class EngagementMessageChannel(str, enum.Enum):
    CLIENT_SERVICE_DELIVERY = "client_service_delivery"
    SERVICE_DELIVERY_PENTESTER = "service_delivery_pentester"

class AssessmentType(str, enum.Enum):
    WEB_APPLICATION = "web_application"
    MOBILE_APPLICATION = "mobile_application"
    API = "api"
    NETWORK = "network"
    CLOUD = "cloud"
    OTHER = "other"

class NotificationType(str, Enum):
    ENGAGEMENT_REQUESTED = "engagement.requested"
    ENGAGEMENT_ASSIGNED = "engagement.assigned"
    ENGAGEMENT_SCHEDULED = "engagement.scheduled"
    ENGAGEMENT_REASSIGNED = "engagement.reassigned"
    ENGAGEMENT_RESCHEDULED = "engagement.rescheduled"
    ENGAGEMENT_STARTED = "engagement.started"
    ENGAGEMENT_REVIEW_REQUIRED = "engagement.review_required"
    ENGAGEMENT_REVIEW_RETURNED = "engagement.review_returned"
    ENGAGEMENT_COMPLETED = "engagement.completed"
    ENGAGEMENT_CANCELLED = "engagement.cancelled"
    MESSAGE_RECEIVED = "message.received"
    RETEST_REQUESTED = "retest.requested"
    RETEST_COMPLETED = "retest.completed"
    REPORT_READY = "report.ready"
