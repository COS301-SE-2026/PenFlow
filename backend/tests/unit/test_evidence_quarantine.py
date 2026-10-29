import struct
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services import evidence_quarantine_service as quarantine
from app.services import malware_service as malware


@pytest.mark.parametrize(
    "reply,status",
    [
        (b"stream: OK", "clean"),
        (b"stream: Eicar-Signature FOUND", "rejected"),
        (b"stream: Heuristics.Limits.Exceeded FOUND", "rejected"),
    ],
)
def test_verdict(reply, status):
    assert malware.parse_reply(reply, "version").status == status


@pytest.mark.parametrize(
    "reply",
    [
        b"",
        b"OK",
        b"stream: Access denied ERROR",
        b"stream: OK\nmalicious",
    ],
)
def test_invalid_verdict(reply):
    with pytest.raises(RuntimeError):
        malware.parse_reply(reply, "version")


@pytest.mark.parametrize(
    "status",
    ["pending", "failed", "rejected", "unknown"],
)
def test_blocks_uncleared_downloads(status):
    with pytest.raises(HTTPException):
        quarantine.require_clean(
            SimpleNamespace(quarantine_status=status)
        )


def test_clean_requires_completed_metadata():
    with pytest.raises(HTTPException):
        quarantine.require_clean(
            SimpleNamespace(
                quarantine_status="clean",
                sha256=None,
            )
        )


def test_clean_download_allowed():
    quarantine.require_clean(
        SimpleNamespace(
            quarantine_status="clean",
            sha256="a" * 64,
            size_bytes=5,
            scanned_at=datetime.now(timezone.utc),
        )
    )


@pytest.mark.parametrize("stale", [False, True])
def test_protocol_and_signature_freshness(monkeypatch, stale):
    updated = datetime.now(timezone.utc) - timedelta(
        days=8 if stale else 1
    )
    version = (
        f"ClamAV 1.4/12345/"
        f"{updated.strftime('%a %b %d %H:%M:%S %Y')}"
    ).encode()

    version_socket = MagicMock()
    version_socket.__enter__.return_value = version_socket
    version_socket.recv.return_value = version + b"\0"

    scan_socket = MagicMock()
    scan_socket.__enter__.return_value = scan_socket
    scan_socket.recv.return_value = b"stream: OK\0"

    connect = Mock(
        side_effect=[version_socket, scan_socket]
    )
    monkeypatch.setenv("CLAMAV_HOST", "127.0.0.1")
    monkeypatch.setattr(
        malware.socket,
        "create_connection",
        connect,
    )

    if stale:
        with pytest.raises(RuntimeError, match="stale"):
            malware.scan_bytes(b"proof")

        assert connect.call_count == 1

    else:
        assert malware.scan_bytes(b"proof").status == "clean"

        transmitted = b"".join(
            call.args[0]
            for call in scan_socket.sendall.call_args_list
        )
        assert transmitted == (
            b"zINSTREAM\0"
            + struct.pack("!I", 5)
            + b"proof"
            + struct.pack("!I", 0)
        )


def setup_job(monkeypatch, *, result="clean", attempt=0):
    evidence = SimpleNamespace(
        id=uuid4(),
        finding_id=uuid4(),
        file_name="proof.txt",
        mime_type="text/plain",
        uploaded_at=datetime.now(timezone.utc),
        scan_attempts=attempt,
        storage_backend="local",
        file_path="key",
        sha256=None,
        size_bytes=None,
        quarantine_status="pending",
        scan_message=None,
        scanned_at=None,
        scanner_version=None,
        next_scan_at=datetime.now(timezone.utc),
    )
    finding = SimpleNamespace(
        id=evidence.finding_id,
        engagement_id=uuid4(),
    )
    db = SimpleNamespace(
        info={},
        scalar=AsyncMock(return_value=evidence),
        get=AsyncMock(return_value=finding),
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )

    storage = Mock()
    storage.read.return_value = b"proof"

    monkeypatch.setattr(
        quarantine,
        "EvidenceStorageService",
        Mock(return_value=storage),
    )

    scanner = Mock()

    if result == "error":
        scanner.side_effect = TimeoutError()
    else:
        scanner.return_value = malware.MalwareVerdict(
            result,
            "message",
            "version",
        )

    monkeypatch.setattr(
        quarantine,
        "scan_bytes",
        scanner,
    )

    async def run_inline(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(
        quarantine,
        "run_in_threadpool",
        run_inline,
    )

    audit = AsyncMock()
    monkeypatch.setattr(
        quarantine.AuditRepository,
        "create_log",
        audit,
    )

    return db, evidence, audit


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "result,attempt,expected",
    [
        ("clean", 0, "clean"),
        ("rejected", 0, "rejected"),
        ("error", 0, "pending"),
        ("error", 2, "failed"),
    ],
)
async def test_processing_states(
    monkeypatch,
    result,
    attempt,
    expected,
):
    db, evidence, audit = setup_job(
        monkeypatch,
        result=result,
        attempt=attempt,
    )

    assert await quarantine.EvidenceQuarantineService.process_one(db)
    assert evidence.quarantine_status == expected
    db.commit.assert_awaited_once()

    if expected == "pending":
        audit.assert_not_awaited()
    else:
        assert audit.call_args.kwargs["commit"] is False


@pytest.mark.asyncio
async def test_no_pending_job():
    db = SimpleNamespace(
        scalar=AsyncMock(return_value=None),
        rollback=AsyncMock(),
    )

    assert not await quarantine.EvidenceQuarantineService.process_one(db)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    ["success", "unassigned", "clean", "pending", "rejected"],
)
async def test_retry_permissions_and_state(monkeypatch, case):
    db, evidence, audit = setup_job(monkeypatch)

    evidence.quarantine_status = (
        "failed"
        if case in {"success", "unassigned"}
        else case
    )
    evidence.scan_attempts = 3

    owned = AsyncMock()

    if case == "unassigned":
        owned.side_effect = HTTPException(
            403,
            "Not assigned",
        )

    monkeypatch.setattr(
        quarantine.ServiceDeliveryService,
        "require_owned_engagement",
        owned,
    )

    if case == "success":
        response = await quarantine.EvidenceQuarantineService.retry(
            db,
            evidence_id=evidence.id,
            user_id=uuid4(),
        )

        assert response.quarantine_status == "pending"
        assert evidence.scan_attempts == 0
        db.commit.assert_awaited_once()

    else:
        with pytest.raises(HTTPException):
            await quarantine.EvidenceQuarantineService.retry(
                db,
                evidence_id=evidence.id,
                user_id=uuid4(),
            )

        audit.assert_not_awaited()
        db.commit.assert_not_awaited()
        db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_audit_failure_rolls_back(monkeypatch):
    db, _, audit = setup_job(monkeypatch)
    audit.side_effect = RuntimeError("Audit failure")

    with pytest.raises(RuntimeError):
        await quarantine.EvidenceQuarantineService.process_one(db)

    db.commit.assert_not_awaited()
    db.rollback.assert_awaited_once()