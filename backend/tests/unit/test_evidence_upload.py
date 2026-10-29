from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.routes import findings as routes
from app.services.evidence_storage_service import StoredEvidence


@pytest.fixture(autouse=True)
def inline_storage_calls(monkeypatch):
    async def run_inline(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(routes, "run_in_threadpool", run_inline)


@pytest.mark.asyncio
async def test_denied_upload_does_not_read_file(monkeypatch):
    monkeypatch.setattr(
        routes.FindingService,
        "require_editable_finding",
        AsyncMock(side_effect=HTTPException(404, "Not found")),
    )

    storage_factory = Mock()
    monkeypatch.setattr(
        routes,
        "EvidenceStorageService",
        storage_factory,
    )

    file = SimpleNamespace(
        read=AsyncMock(),
        content_type="text/plain",
    )

    with pytest.raises(HTTPException):
        await routes.upload_finding_evidence(
            uuid4(),
            file=file,
            db=Mock(),
            user=SimpleNamespace(id=uuid4()),
        )

    file.read.assert_not_awaited()
    storage_factory.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("persisted", [None, uuid4()])
async def test_cleanup_only_when_record_absent(
    monkeypatch,
    persisted,
):
    monkeypatch.setattr(
        routes.FindingService,
        "require_editable_finding",
        AsyncMock(
            return_value=SimpleNamespace(
                engagement_id=uuid4(),
            )
        ),
    )
    monkeypatch.setattr(
        routes.FindingService,
        "register_evidence",
        AsyncMock(
            side_effect=RuntimeError("Database failure")
        ),
    )
    monkeypatch.setattr(
        routes,
        "validate_evidence_file",
        Mock(return_value="text/plain"),
    )

    stored = StoredEvidence(
        storage_backend="local",
        file_path="unique-key",
        sha256="a" * 64,
        size_bytes=5,
    )

    storage = Mock()
    storage.store.return_value = stored

    monkeypatch.setattr(
        routes,
        "EvidenceStorageService",
        Mock(return_value=storage),
    )

    db = SimpleNamespace(
        rollback=AsyncMock(),
        scalar=AsyncMock(return_value=persisted),
    )
    file = SimpleNamespace(
        read=AsyncMock(return_value=b"proof"),
        content_type="text/plain",
        filename="proof.txt",
    )

    with pytest.raises(RuntimeError, match="Database failure"):
        await routes.upload_finding_evidence(
            uuid4(),
            file=file,
            db=db,
            user=SimpleNamespace(id=uuid4()),
        )

    assert storage.delete.call_count == (
        1 if persisted is None else 0
    )