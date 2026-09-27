from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class RAGIndexResponse(BaseModel):
    total_findings: int
    indexed: int
    unchanged: int


class RAGQuestionRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=1000,
    )

    limit: int = Field(
        default=5,
        ge=1,
        le=10,
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        stripped = value.strip()

        if not stripped:
            raise ValueError(
                "Question cannot be blank."
            )

        return stripped


class RAGSearchRequest(RAGQuestionRequest):
    pass


class RAGAskRequest(RAGQuestionRequest):
    pass


class RAGAnswerSource(BaseModel):
    finding_id: UUID
    title: str
    severity: str
    evidence_content: str = Field(
        default="",
        exclude=True,
        repr=False,
    )
    cvss_score: float | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )
    cve_id: str | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )
    status: str | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )
    is_verified: bool | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )
    domain: str | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )
    asset_identifier: str | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )
    service_host: str | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )
    service_port: int | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )
    service_protocol: str | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )


class RAGAskResponse(BaseModel):
    question: str
    answer: str
    sources: list[RAGAnswerSource]
    

class RAGSearchResult(BaseModel):
    finding_id: UUID
    title: str
    severity: str
    distance: float
    content: str
    cvss_score: float | None = None
    cve_id: str | None = None
    status: str | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )
    is_verified: bool | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )
    domain: str | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )
    asset_identifier: str | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )
    service_host: str | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )
    service_port: int | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )
    service_protocol: str | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )


class RAGSearchResponse(BaseModel):
    question: str
    results: list[RAGSearchResult]