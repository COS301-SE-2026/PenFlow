from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AssistantFindingClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: UUID
    severity: str | None = None
    cvss_score: float | None = Field(
        default=None,
        ge=0,
        le=10,
    )
    cves: list[str] = Field(default_factory=list)

    @field_validator("severity")
    @classmethod
    def normalize_severity(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized = value.strip().casefold()

        if not normalized:
            return None

        if normalized == "informational":
            return "info"

        return normalized


    @field_validator("cves")
    @classmethod
    def normalize_cves(
        cls,
        values: list[str],
    ) -> list[str]:
        return [
            value.strip().upper()
            for value in values
            if value.strip()
        ]


class AssistantGeneratedFindingAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1)
    cited_finding_ids: list[UUID] = Field(
        default_factory=list,
    )
    links: list[str] = Field(default_factory=list)
    insufficient_evidence: bool
    claims: list[AssistantFindingClaim] = Field(
        default_factory=list,
    )

    @field_validator("answer")
    @classmethod
    def normalize_answer(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError("Generated answer cannot be blank.")

        return normalized
