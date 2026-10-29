import json
from uuid import uuid4

import pytest

from app.schemas.assistant import AssistantAnswerState
from app.schemas.rag import RAGAnswerSource
from app.services.assistant_answer_validator import (
    AssistantFindingEvidence,
)
from app.services.assistant_service import AssistantService


def structured_answer(
    finding_id,
    *,
    cve: str = "CVE-2026-12345",
) -> str:
    return json.dumps(
        {
            "answer": (
                f"Review {cve} "
                f"[Finding ID: {finding_id}]."
            ),
            "cited_finding_ids": [
                str(finding_id)
            ],
            "links": [],
            "insufficient_evidence": False,
            "claims": [
                {
                    "finding_id": str(finding_id),
                    "severity": "high",
                    "cvss_score": 8.1,
                    "cves": [cve],
                }
            ],
        }
    )


def finding_evidence(
    finding_id,
) -> AssistantFindingEvidence:
    return AssistantFindingEvidence(
        finding_id=finding_id,
        severity="high",
        cvss_score=8.1,
        cves=("CVE-2026-12345",),
    )


def test_structured_finalizer_accepts_grounded_answer() -> None:
    finding_id = uuid4()

    result = (
        AssistantService
        .finalize_structured_finding_answer(
            raw_output=structured_answer(
                finding_id
            ),
            evidence=[
                finding_evidence(finding_id)
            ],
        )
    )

    assert "CVE-2026-12345" in result.answer
    assert f"[Finding ID: {finding_id}]" in result.answer
    assert "couldn't safely validate" not in result.answer
    assert (
        result.answer_state
        == AssistantAnswerState.COMPLETE
    )


@pytest.mark.parametrize(
    ("generated_answer", "expected_reason"),
    [
        ("   ", "empty_generation"),
        (
            "Private evidence marker: CVE-2099-9999999",
            "unsupported_reference",
        ),
    ],
)
def test_structured_validation_failure_is_safe_and_bounded(
    caplog: pytest.LogCaptureFixture,
    generated_answer: str,
    expected_reason: str,
) -> None:
    finding_id = uuid4()

    with caplog.at_level(
        "WARNING",
        logger=(
            "app.services."
            "assistant_validation_telemetry"
        ),
    ):
        result = (
            AssistantService
            .finalize_structured_finding_answer(
                raw_output=generated_answer,
                evidence=[
                    finding_evidence(finding_id)
                ],
            )
        )

    events = [
        record.getMessage()
        for record in caplog.records
        if record.name
        == (
            "app.services."
            "assistant_validation_telemetry"
        )
    ]

    assert events == [
        "assistant_answer_validation "
        f"outcome=rejected reason={expected_reason} count=1"
    ]
    assert "couldn't safely validate" in result.answer
    assert f"[Finding ID: {finding_id}]" in result.answer
    assert (
        result.answer_state
        == AssistantAnswerState.VALIDATION_FALLBACK
    )
    assert str(finding_id) not in events[0]
    assert "Private evidence marker" not in events[0]
    assert "CVE-2099-9999999" not in events[0]


def test_rag_source_excludes_internal_grounding_fields() -> None:
    finding_id = uuid4()

    source = RAGAnswerSource(
        finding_id=finding_id,
        title="Example finding",
        severity="high",
        evidence_content=(
            "Internal evidence for CVE-2026-12345."
        ),
        cvss_score=8.1,
        cve_id="CVE-2026-12345",
    )

    assert source.model_dump() == {
        "finding_id": finding_id,
        "title": "Example finding",
        "severity": "high",
    }


def test_structured_finalizer_reports_insufficient_evidence() -> None:
    finding_id = uuid4()

    raw_output = json.dumps(
        {
            "answer": (
                "The supplied evidence is insufficient "
                "to answer this question."
            ),
            "cited_finding_ids": [],
            "links": [],
            "insufficient_evidence": True,
            "claims": [],
        }
    )

    result = (
        AssistantService
        .finalize_structured_finding_answer(
            raw_output=raw_output,
            evidence=[
                finding_evidence(finding_id)
            ],
        )
    )

    assert result.answer.startswith(
        "The supplied evidence is insufficient"
    )
    assert (
        result.answer_state
        == AssistantAnswerState.INSUFFICIENT_EVIDENCE
    )