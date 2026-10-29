import hashlib
import io
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services import evidence_storage_service as module


@pytest.fixture
def storage(monkeypatch, tmp_path):
    monkeypatch.setenv("EVIDENCE_STORAGE", "local")
    monkeypatch.setenv("EVIDENCE_STORAGE_DIR", str(tmp_path))
    return module.EvidenceStorageService()


def store_proof(storage):
    return storage.store(
        engagement_id=uuid4(),
        finding_id=uuid4(),
        contents=b"proof",
        mime_type="text/plain",
    )


def test_local_roundtrip(storage):
    record = store_proof(storage)

    assert storage.read(**vars(record)) == b"proof"
    assert record.sha256 == hashlib.sha256(b"proof").hexdigest()

    storage.delete(
        storage_backend=record.storage_backend,
        file_path=record.file_path,
    )

    with pytest.raises(HTTPException) as caught:
        storage.read(**vars(record))

    assert caught.value.status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "../secret",
        "/etc/passwd",
        "engagements/../../secret",
    ],
)
def test_rejects_paths(storage, path):
    with pytest.raises(HTTPException):
        storage.read(
            storage_backend="local",
            file_path=path,
            sha256=None,
            size_bytes=None,
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("sha256", "0" * 64),
        ("size_bytes", 99),
    ],
)
def test_detects_tampering(storage, field, value):
    values = vars(store_proof(storage)).copy()
    values[field] = value

    with pytest.raises(HTTPException) as caught:
        storage.read(**values)

    assert caught.value.status_code == 503


def test_s3_roundtrip(monkeypatch):
    monkeypatch.setenv("EVIDENCE_STORAGE", "s3")
    monkeypatch.setenv("EVIDENCE_S3_BUCKET", "test-evidence")

    client = Mock()
    monkeypatch.setattr(
        module.boto3,
        "client",
        Mock(return_value=client),
    )

    storage = module.EvidenceStorageService()
    record = store_proof(storage)

    assert (
        client.put_object.call_args.kwargs["ServerSideEncryption"]
        == "AES256"
    )

    body = io.BytesIO(b"proof")
    client.get_object.return_value = {"Body": body}

    assert storage.read(**vars(record)) == b"proof"
    assert body.closed

    storage.delete(
        storage_backend="s3",
        file_path=record.file_path,
    )

    client.delete_object.assert_called_once_with(
        Bucket="test-evidence",
        Key=record.file_path,
    )


def test_no_local_fallback(storage):
    with pytest.raises(HTTPException) as caught:
        storage.read(
            storage_backend="s3",
            file_path="ignored",
            sha256=None,
            size_bytes=None,
        )

    assert caught.value.status_code == 503


def test_legacy_local(storage):
    path = storage.root / "old.txt"
    path.write_bytes(b"legacy")

    assert storage.read(
        storage_backend="local",
        file_path=str(path),
        sha256=None,
        size_bytes=None,
    ) == b"legacy"


def test_bounded_download(storage):
    path = storage.root / "old.txt"
    path.write_bytes(b"x" * (module.MAX_EVIDENCE_BYTES + 1))

    with pytest.raises(HTTPException):
        storage.read(
            storage_backend="local",
            file_path=str(path),
            sha256=None,
            size_bytes=None,
        )