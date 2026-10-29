import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.middleware.auth import require_user
from app.api.middleware.rate_limiter import limiter
from app.api.routes import assistant as assistant_routes
from app.api.routes.assistant import router
from app.models.base import RAGIndexStatus
from app.schemas.assistant import (
    AssistantSource,
    AssistantSourceType,
)
from app.schemas.rag import RAGSearchResult
from app.schemas.security_intelligence import SecurityPriorityFinding
from app.services import assistant_service
from app.services.assistant_answer_validator import (
    AssistantFindingEvidence,
)
from app.services.assistant_context_service import (
    AssistantContextService,
    FindingContextResult,
)
from app.services.rag.rag_service import RAGService
from app.services.scan_service import ScanService
from app.services.security_intelligence_service import (
    SecurityIntelligenceService,
)
from app.utils.db import get_db


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "strategy",
    ["risk", "semantic", "finding"],
)
@pytest.mark.parametrize(
    "generation_case",
    [
        "invented_uuid",
        "invented_cve",
        "unauthorized_citation",
        "empty",
        "whitespace",
        "grounded",
    ],
)
async def test_grounding_preserves_safe_http_response(
    monkeypatch: pytest.MonkeyPatch,
    strategy: str,
    generation_case: str,
) -> None:
    scan_id = uuid4()
    finding_id = uuid4()
    invented_id = uuid4()
    user = SimpleNamespace(id=uuid4())
    db = AsyncMock()

    allowed_cve = "CVE-2026-12345"
    invented_cve = "CVE-2099-9999999"
    evidence = f"Recorded vulnerability: {allowed_cve}."
    def structured_answer(
        answer: str,
        *,
        cited_id=finding_id,
        cve: str = allowed_cve,
    ) -> str:
        return json.dumps(
            {
                "answer": answer,
                "cited_finding_ids": [
                    str(cited_id)
                ],
                "links": [],
                "insufficient_evidence": False,
                "claims": [
                    {
                        "finding_id": str(cited_id),
                        "severity": "high",
                        "cvss_score": 8.1,
                        "cves": [cve],
                    }
                ],
            }
        )

    generated_answers = {
        "invented_uuid": structured_answer(
            (
                f"The related record is {invented_id} "
                f"[Finding ID: {finding_id}]."
            )
        ),
        "invented_cve": structured_answer(
            (
                f"This finding is associated with {invented_cve} "
                f"[Finding ID: {finding_id}]."
            ),
            cve=invented_cve,
        ),
        "unauthorized_citation": structured_answer(
            (
                "Review this issue "
                f"[Finding ID: {invented_id}]."
            ),
            cited_id=invented_id,
        ),
        "empty": "",
        "whitespace": " \n\t ",
        "grounded": structured_answer(
            (
                f"The supplied evidence records {allowed_cve} "
                f"[Finding ID: {finding_id}]."
            )
        ),
    }

    generation = SimpleNamespace(
        model="test-model",
        generate=AsyncMock(
            return_value=generated_answers[generation_case],
        ),
    )
    monkeypatch.setattr(
        assistant_service,
        "create_generation_provider",
        lambda: generation,
    )
    monkeypatch.setattr(
        assistant_service,
        "create_embedding_provider",
        lambda: SimpleNamespace(model="test-model"),
    )

    access_check = AsyncMock(
        return_value=SimpleNamespace(
            id=scan_id,
            rag_index_status=RAGIndexStatus.PENDING,
            rag_document_schema_version=None,
            rag_embedding_model=None,
        ),
    )
    monkeypatch.setattr(
        ScanService,
        "require_scan_access",
        access_check,
    )

    expected_capability = "security_analysis"
    request_context = {
        "page": "scan",
        "scan_id": str(scan_id),
    }

    if strategy == "risk":
        question = "What should I remediate first?"
        expected_intent = "risk_prioritization"

        monkeypatch.setattr(
            SecurityIntelligenceService,
            "prioritize_scan_findings",
            AsyncMock(
                return_value=[
                    SecurityPriorityFinding(
                        finding_id=finding_id,
                        priority=1,
                        title="Authorized vulnerability",
                        severity="high",
                        cvss_score=8.1,
                        cve_id=allowed_cve,
                        status="open",
                        is_verified=True,
                        priority_reasons=["High severity"],
                        content=evidence,
                    )
                ],
            ),
        )
    elif strategy == "finding":
        question = "Explain this finding."
        expected_capability = "finding_explanation"
        expected_intent = None
        request_context = {
            "page": "finding",
            "finding_id": str(finding_id),
        }

        monkeypatch.setattr(
            AssistantContextService,
            "get_finding_context",
            AsyncMock(
                return_value=FindingContextResult(
                    evidence=evidence,
                    sources=[
                        AssistantSource(
                            source_type=AssistantSourceType.FINDING,
                            source_id=str(finding_id),
                            title="Authorized vulnerability",
                            severity="high",
                            href=(
                                f"/phase2_scan/results/{scan_id}/findings"
                                f"?finding={finding_id}"
                            ),
                        )
                    ],
                    grounding_evidence=(
                        AssistantFindingEvidence(
                            finding_id=finding_id,
                            severity="high",
                            cvss_score=8.1,
                            cves=(allowed_cve,),
                        ),
                    ),
                    authorized_entity_ids=(
                        finding_id,
                        scan_id,
                    ),
                    allowed_links=(
                        (
                            f"/phase2_scan/results/"
                            f"{scan_id}/findings"
                            f"?finding={finding_id}"
                        ),
                    ),
                    links=[],
                )
            ),
        )

    else:
        question = "Are there authentication weaknesses?"
        expected_intent = "semantic_search"

        monkeypatch.setattr(
            RAGService,
            "index_scan_findings",
            AsyncMock(),
        )
        monkeypatch.setattr(
            RAGService,
            "search_scan",
            AsyncMock(
                return_value=[
                    RAGSearchResult(
                        finding_id=finding_id,
                        title="Authorized vulnerability",
                        severity="high",
                        distance=0.1,
                        content=evidence,
                        cvss_score=8.1,
                        cve_id=allowed_cve,
                    )
                ],
            ),
        )

    # Isolate the real assistant route from unrelated app middleware.
    # Authentication and evidence access are supplied by test fixtures.
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[require_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db

    # Rate limiting is outside this test's scope.
    monkeypatch.setattr(limiter, "enabled", False)

    # Grounding is under test; Redis concurrency is tested separately.
    @asynccontextmanager
    async def allow_ai_request(user_id):
        yield

    monkeypatch.setattr(
        assistant_routes,
        "ai_request_slot",
        allow_ai_request,
    )

    async with AsyncClient(
        transport=ASGITransport(
            app=app,
            raise_app_exceptions=False,
        ),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/assistant/query",
            json={
                "question": question,
                "context": request_context,
            },
        )

    assert response.status_code == 200, response.text

    if strategy == "finding":
        access_check.assert_not_awaited()
        AssistantContextService.get_finding_context.assert_awaited_once()
    else:
        access_check.assert_awaited_once_with(
            db,
            scan_id=scan_id,
            user_id=user.id,
        )
    generation.generate.assert_awaited_once()

    body = response.json()
    answer = body["answer"]

    expected_answer_state = (
        "complete"
        if generation_case == "grounded"
        else "validation_fallback"
    )

    assert (
        body["answer_state"]
        == expected_answer_state
    )

    assert body["capability"] == expected_capability
    assert body["security_intent"] == expected_intent
    assert answer.strip()
    assert str(invented_id) not in answer
    assert invented_cve not in answer
    assert f"[Finding ID: {finding_id}]" in answer

    assert len(body["sources"]) == 1
    source = body["sources"][0]
    assert source["source_type"] == "finding"
    assert source["source_id"] == str(finding_id)
    assert source["title"] == "Authorized vulnerability"
    assert source["severity"] == "high"
    assert source["href"] == (
        f"/phase2_scan/results/{scan_id}/findings"
        f"?finding={finding_id}"
    )
    assert "evidence_content" not in source

    if generation_case in {"invented_uuid", "invented_cve"}:
        assert "couldn't safely validate" in answer

    elif generation_case in {"empty", "whitespace"}:
        if strategy == "semantic":
            assert "couldn't safely validate" in answer
        else:
            assert "couldn't safely validate" in answer

    elif generation_case == "grounded":
        assert allowed_cve in answer
        assert "couldn't safely validate" not in answer
        assert "couldn't generate an explanation" not in answer


@pytest.fixture(autouse=True)
def mock_scan_overview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.services.assistant_scan_snapshot.collect_scan_snapshot",
        AsyncMock(
            return_value=(
                '{"scan_overview":'
                '{"availability":"test_snapshot"}}'
            )
        ),
    )