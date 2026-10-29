from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import Request
from fastapi.responses import Response

from app.api.middleware import audit


def request(path, params=None):
    req = Request({
        "type": "http",
        "method": "GET",
        "path": path,
        "query_string": b"token=SECRET",
        "headers": [(b"authorization", b"SECRET")],
        "route": SimpleNamespace(
            path="/api/v1/reports/{report_id}/download",
        ),
        "path_params": params or {},
    })
    req.state.audit_phase3_report = True
    return req


@pytest.mark.parametrize("status", [200, 401, 403, 404])
def test_non_phase3_report_events_are_excluded(status):
    req = request("/api/v1/reports/123/download")
    req.state.audit_phase3_report = False

    assert audit.event_for(req, status) is None
    

@pytest.mark.asyncio
async def test_failed_audit_blocks_download(monkeypatch):
    monkeypatch.setattr(
        audit,
        "record_event",
        AsyncMock(side_effect=RuntimeError()),
    )

    response = await audit.audit_sensitive_requests(
        request("/api/v1/reports/123/download"),
        AsyncMock(return_value=Response(status_code=200)),
    )

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_failed_rejection_audit_preserves_rejection(monkeypatch):
    monkeypatch.setattr(
        audit,
        "record_event",
        AsyncMock(side_effect=RuntimeError()),
    )

    response = await audit.audit_sensitive_requests(
        request("/api/v1/reports/123/download"),
        AsyncMock(return_value=Response(status_code=404)),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_audit_uses_verified_identity_and_excludes_secrets(monkeypatch):
    report_id, engagement_id, user_id = uuid4(), uuid4(), uuid4()

    db = SimpleNamespace(
        scalar=AsyncMock(return_value=user_id),
        get=AsyncMock(
            return_value=SimpleNamespace(
                engagement_id=engagement_id,
            ),
        ),
    )

    @asynccontextmanager
    async def factory():
        yield db

    log = AsyncMock()

    monkeypatch.setattr(audit, "SessionLocal", factory)
    monkeypatch.setattr(audit.AuditRepository, "create_log", log)

    req = request(
        f"/api/v1/reports/{report_id}/download",
        {"report_id": report_id},
    )
    req.state.audit_subject = "verified-provider-subject"

    await audit.record_event(
        req,
        "report.download_authorised",
        200,
    )

    data = log.await_args.kwargs

    assert data["user_id"] == user_id
    assert data["metadata"]["engagement_id"] == str(engagement_id)
    assert "SECRET" not in str(data)
    assert "verified-provider-subject" not in str(data["metadata"])


def test_missing_record_is_not_claimed_to_be_a_proven_denial():
    req = request("/api/v1/reports/123/download")

    assert audit.event_for(req, 404) == "sensitive_request.rejected"


def test_download_event_does_not_claim_completed_delivery():
    req = request("/api/v1/reports/123/download")

    assert audit.event_for(req, 200) == "report.download_authorised"