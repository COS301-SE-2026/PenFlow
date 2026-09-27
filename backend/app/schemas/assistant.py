from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class AssistantCapability(str, Enum):
    PRODUCT_HELP = "product_help"
    NAVIGATION = "navigation"
    USER_DATA = "user_data"
    FINDING_EXPLANATION = "finding_explanation"
    SECURITY_ANALYSIS = "security_analysis"
    UNSUPPORTED = "unsupported"


class AssistantAudience(str, Enum):
    EXECUTIVE = "executive"
    IT_MANAGER = "it_manager"
    DEVELOPER = "developer"
    SECURITY = "security"


class AssistantPage(str, Enum):
    GENERAL = "general"
    DASHBOARD = "dashboard"
    DOMAINS = "domains"
    SCHEDULED_SCANS = "scheduled_scans"
    SCAN = "scan"
    FINDING = "finding"
    ENGAGEMENT = "engagement"
    REPORT = "report"


class AssistantSourceType(str, Enum):
    FINDING = "finding"
    PRODUCT_GUIDE = "product_guide"
    USER_DATA = "user_data"
    NAVIGATION = "navigation"


class AssistantContext(BaseModel):
    page: AssistantPage = AssistantPage.GENERAL
    scan_id: UUID | None = None
    finding_id: UUID | None = None
    engagement_id: UUID | None = None
    timezone: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
    )


class AssistantConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(
        min_length=1,
        max_length=2000,
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "Conversation messages cannot be blank."
            )

        return normalized


class AssistantQueryRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=1000,
    )
    context: AssistantContext = Field(
        default_factory=AssistantContext,
    )
    audience: AssistantAudience = AssistantAudience.SECURITY

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Question cannot be blank.")

        return normalized

    history: list[AssistantConversationMessage] = Field(
        default_factory=list,
        max_length=6,
    )
    previous_capability: AssistantCapability | None = None


class AssistantSource(BaseModel):
    source_type: AssistantSourceType
    source_id: str
    title: str
    severity: str | None = None
    href: str | None = Field(
        default=None,
        pattern=r"^/",
    )


class AssistantLink(BaseModel):
    label: str
    href: str = Field(pattern=r"^/")


class SecurityQueryIntent(str, Enum):
    RISK_PRIORITIZATION = "risk_prioritization"
    EXACT_LOOKUP = "exact_lookup"
    SEMANTIC_SEARCH = "semantic_search"
    SCAN_COMPARISON = "scan_comparison"
    PORTFOLIO_ANALYSIS = "portfolio_analysis"
    SCAN_SUMMARY = "scan_summary"


class AssistantQueryResponse(BaseModel):
    question: str
    answer: str = Field(min_length=1)
    capability: AssistantCapability
    sources: list[AssistantSource] = Field(default_factory=list)
    links: list[AssistantLink] = Field(default_factory=list)
    security_intent: SecurityQueryIntent | None = None