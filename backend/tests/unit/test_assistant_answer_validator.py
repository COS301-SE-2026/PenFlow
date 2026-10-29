import json
from uuid import uuid4

import pytest

from app.services.assistant_answer_validator import (
    AssistantAnswerValidationError,
    AssistantAnswerValidator,
    AssistantFindingEvidence,
)


def structured_output(
    *,
    finding_id,
    answer: str | None = None,
    severity: str | None = "high",
    cvss_score: float | None = 8.1,
    cves: list[str] | None = None,
    links: list[str] | None = None,
    insufficient_evidence: bool = False,
) -> str:
    return json.dumps(
        {
            "answer": (
                answer
                or (
                    "Investigate the high-severity finding with "
                    "CVSS 8.1 and CVE-2026-12345 "
                    f"[Finding ID: {finding_id}]."
                )
            ),
            "cited_finding_ids": (
                []
                if insufficient_evidence
                else [str(finding_id)]
            ),
            "links": (
                []
                if insufficient_evidence
                else (
                    links
                    if links is not None
                    else [f"/findings/{finding_id}"]
                )
            ),
            "insufficient_evidence": (
                insufficient_evidence
            ),
            "claims": (
                []
                if insufficient_evidence
                else [
                    {
                        "finding_id": str(finding_id),
                        "severity": severity,
                        "cvss_score": cvss_score,
                        "cves": (
                            cves
                            if cves is not None
                            else ["CVE-2026-12345"]
                        ),
                    }
                ]
            ),
        }
    )


def finding_evidence(finding_id):
    return AssistantFindingEvidence(
        finding_id=finding_id,
        severity="high",
        cvss_score=8.1,
        cves=("CVE-2026-12345",),
    )


def test_accepts_grounded_structured_output() -> None:
    finding_id = uuid4()
    link = f"/findings/{finding_id}"

    result = AssistantAnswerValidator.validate_structured(
        raw_output=structured_output(
            finding_id=finding_id,
            links=[link],
        ),
        evidence=[finding_evidence(finding_id)],
        allowed_entity_ids=[finding_id],
        allowed_links=[link],
    )

    assert result.answer
    assert result.cited_finding_ids == [finding_id]
    assert result.claims[0].severity == "high"
    assert result.claims[0].cvss_score == 8.1


def test_accepts_json_code_fence() -> None:
    finding_id = uuid4()
    link = f"/findings/{finding_id}"
    raw_output = structured_output(
        finding_id=finding_id,
        links=[link],
    )

    result = AssistantAnswerValidator.validate_structured(
        raw_output=f"```json\n{raw_output}\n```",
        evidence=[finding_evidence(finding_id)],
        allowed_links=[link],
    )

    assert result.cited_finding_ids == [finding_id]


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("severity", "critical", "severity"),
        ("cvss_score", 9.9, "CVSS"),
        ("cves", ["CVE-2099-9999999"], "CVE"),
    ],
)
def test_rejects_mismatched_structured_claim(
    field: str,
    value: object,
    error: str,
) -> None:
    finding_id = uuid4()
    arguments = {
        "severity": "high",
        "cvss_score": 8.1,
        "cves": ["CVE-2026-12345"],
    }
    arguments[field] = value

    with pytest.raises(
        AssistantAnswerValidationError,
        match=error,
    ):
        AssistantAnswerValidator.validate_structured(
            raw_output=structured_output(
                finding_id=finding_id,
                **arguments,
            ),
            evidence=[finding_evidence(finding_id)],
            allowed_links=[
                f"/findings/{finding_id}"
            ],
        )


def test_rejects_invented_entity_identifier() -> None:
    finding_id = uuid4()
    invented_id = uuid4()
    link = f"/findings/{finding_id}"

    with pytest.raises(
        AssistantAnswerValidationError,
        match="unauthorized entity",
    ):
        AssistantAnswerValidator.validate_structured(
            raw_output=structured_output(
                finding_id=finding_id,
                answer=(
                    f"Related record {invented_id} "
                    f"[Finding ID: {finding_id}]."
                ),
                severity=None,
                cvss_score=None,
                cves=[],
                links=[link],
            ),
            evidence=[finding_evidence(finding_id)],
            allowed_links=[link],
        )


@pytest.mark.parametrize(
    "link",
    [
        "https://evil.example/finding",
        "//evil.example/finding",
        "/admin/internal",
    ],
)
def test_rejects_unapproved_link(link: str) -> None:
    finding_id = uuid4()

    with pytest.raises(
        AssistantAnswerValidationError,
        match="URL",
    ):
        AssistantAnswerValidator.validate_structured(
            raw_output=structured_output(
                finding_id=finding_id,
                links=[link],
            ),
            evidence=[finding_evidence(finding_id)],
            allowed_links=[
                f"/findings/{finding_id}"
            ],
        )


def test_rejects_unapproved_link_inside_answer() -> None:
    finding_id = uuid4()
    approved_link = f"/findings/{finding_id}"

    with pytest.raises(
        AssistantAnswerValidationError,
        match="URL",
    ):
        AssistantAnswerValidator.validate_structured(
            raw_output=structured_output(
                finding_id=finding_id,
                answer=(
                    "Open /admin/internal and review "
                    f"[Finding ID: {finding_id}]."
                ),
                severity=None,
                cvss_score=None,
                cves=[],
                links=[approved_link],
            ),
            evidence=[finding_evidence(finding_id)],
            allowed_links=[approved_link],
        )


def test_rejects_structured_citations_missing_from_answer() -> None:
    finding_id = uuid4()

    with pytest.raises(
        AssistantAnswerValidationError,
        match="did not match",
    ):
        AssistantAnswerValidator.validate_structured(
            raw_output=structured_output(
                finding_id=finding_id,
                answer="Review the supplied finding.",
                severity=None,
                cvss_score=None,
                cves=[],
            ),
            evidence=[finding_evidence(finding_id)],
            allowed_links=[
                f"/findings/{finding_id}"
            ],
        )


def test_accepts_insufficient_evidence_output() -> None:
    finding_id = uuid4()

    result = AssistantAnswerValidator.validate_structured(
        raw_output=structured_output(
            finding_id=finding_id,
            answer=(
                "The supplied evidence is insufficient "
                "to answer this question."
            ),
            insufficient_evidence=True,
        ),
        evidence=[finding_evidence(finding_id)],
        allowed_links=[],
    )

    assert result.insufficient_evidence is True
    assert result.cited_finding_ids == []
    assert result.claims == []


def test_rejects_non_json_structured_output() -> None:
    finding_id = uuid4()

    with pytest.raises(
        AssistantAnswerValidationError,
        match="structured JSON",
    ):
        AssistantAnswerValidator.validate_structured(
            raw_output="This is an ordinary text answer.",
            evidence=[finding_evidence(finding_id)],
        )


@pytest.mark.parametrize(
    "answer",
    [
        (
            "Evidence is insufficient, but review record "
            "77777777-7777-4777-8777-777777777777."
        ),
        (
            "Evidence is insufficient, but this is "
            "CVE-2099-9999999."
        ),
        (
            "Evidence is insufficient, but its CVSS score is 9.9."
        ),
        (
            "Evidence is insufficient, but this has "
            "critical severity."
        ),
        (
            "Evidence is insufficient. Open /admin/internal."
        ),
        (
            "Evidence is insufficient. Visit "
            "https://evil.example/finding."
        ),
    ],
)
def test_insufficient_evidence_rejects_factual_references(
    answer: str,
) -> None:
    finding_id = uuid4()

    with pytest.raises(
        AssistantAnswerValidationError,
    ):
        AssistantAnswerValidator.validate_structured(
            raw_output=structured_output(
                finding_id=finding_id,
                answer=answer,
                insufficient_evidence=True,
            ),
            evidence=[finding_evidence(finding_id)],
        )


@pytest.mark.parametrize(
    "answer",
    [
        "CVSS 9.9",
        "CVSS: 9.9",
        "CVSS score 9.9",
        "CVSS score: 9.9",
        "CVSS score is 9.9",
        "CVSS is 9.9",
        "CVSS of 9.9",
    ],
)
def test_extracts_common_cvss_claim_formats(
    answer: str,
) -> None:
    assert (
        AssistantAnswerValidator.extract_cvss_scores(
            answer
        )
        == {9.9}
    )
