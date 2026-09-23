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


class RAGAskResponse(BaseModel):
    question: str
    answer: str = Field(
        min_length=1
    )
    sources: list[RAGAnswerSource]
    

class RAGSearchResult(BaseModel):
    finding_id: UUID
    title: str
    severity: str
    distance: float
    content: str


class RAGSearchResponse(BaseModel):
    question: str
    results: list[RAGSearchResult]