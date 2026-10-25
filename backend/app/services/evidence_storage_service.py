import hashlib
import hmac
import os
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import HTTPException

MAX_EVIDENCE_BYTES = 10 * 1024 * 1024

EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "text/plain": ".txt",
    "application/json": ".json",
    "application/pdf": ".pdf",
}

_KEY = re.compile(
    r"engagements/[0-9a-f-]{36}/findings/[0-9a-f-]{36}/"
    r"[0-9a-f-]{36}\.(?:png|jpg|txt|json|pdf)"
)


@dataclass(frozen=True)
class StoredEvidence:
    storage_backend: str
    file_path: str
    sha256: str
    size_bytes: int


class EvidenceStorageService:
    def __init__(self):
        self.mode = os.getenv("EVIDENCE_STORAGE", "local")
        self.bucket = os.getenv("EVIDENCE_S3_BUCKET", "")
        self.root = Path(
            os.getenv("EVIDENCE_STORAGE_DIR", "/tmp/penflow-evidence")
        ).resolve()

        if self.mode not in {"local", "s3"}:
            raise RuntimeError("Invalid EVIDENCE_STORAGE")

        if self.mode == "s3" and not self.bucket:
            raise RuntimeError("EVIDENCE_S3_BUCKET is required")

    def _client(self):
        return boto3.client(
            "s3",
            region_name=os.getenv("AWS_REGION", "af-south-1"),
            config=Config(
                connect_timeout=5,
                read_timeout=15,
                retries={"mode": "standard", "max_attempts": 2},
            ),
        )

    @staticmethod
    def _key(value: str) -> str:
        if not _KEY.fullmatch(value):
            raise HTTPException(404, "Evidence file not found")

        return value

    def _local_path(self, value: str) -> Path:
        path = Path(value)

        if not path.is_absolute():
            path = self.root / self._key(value)

        path = path.resolve()

        if not path.is_relative_to(self.root) or path == self.root:
            raise HTTPException(404, "Evidence file not found")

        return path

    def store(
        self,
        *,
        engagement_id: UUID,
        finding_id: UUID,
        contents: bytes,
        mime_type: str,
    ) -> StoredEvidence:
        if not 0 < len(contents) <= MAX_EVIDENCE_BYTES:
            raise HTTPException(413, "Invalid evidence file size")

        suffix = EXTENSIONS.get(mime_type)

        if suffix is None:
            raise HTTPException(415, "Unsupported evidence file type")

        key = (
            f"engagements/{UUID(str(engagement_id))}/"
            f"findings/{UUID(str(finding_id))}/{uuid4()}{suffix}"
        )
        digest = hashlib.sha256(contents).hexdigest()

        if self.mode == "s3":
            self._client().put_object(
                Bucket=self.bucket,
                Key=key,
                Body=contents,
                ContentType=mime_type,
                ServerSideEncryption="AES256",
                Metadata={"sha256": digest},
            )

        else:
            path = self._local_path(key)
            path.parent.mkdir(parents=True, exist_ok=True)

            try:
                with path.open("xb") as handle:
                    handle.write(contents)

            except FileExistsError:
                raise

            except Exception:
                path.unlink(missing_ok=True)
                raise

        return StoredEvidence(self.mode, key, digest, len(contents))

    def read(
        self,
        *,
        storage_backend: str,
        file_path: str,
        sha256: str | None,
        size_bytes: int | None,
    ) -> bytes:
        if storage_backend != self.mode:
            raise HTTPException(
                503,
                "Evidence storage configuration mismatch",
            )

        if self.mode == "s3":
            try:
                result = self._client().get_object(
                    Bucket=self.bucket,
                    Key=self._key(file_path),
                )

            except ClientError as exc:
                if exc.response["Error"]["Code"] in {
                    "NoSuchKey",
                    "404",
                    "NotFound",
                }:
                    raise HTTPException(
                        404,
                        "Evidence file not found",
                    ) from exc

                raise

            body = result["Body"]

            try:
                contents = body.read(MAX_EVIDENCE_BYTES + 1)
            finally:
                body.close()

        else:
            try:
                with self._local_path(file_path).open("rb") as handle:
                    contents = handle.read(MAX_EVIDENCE_BYTES + 1)

            except FileNotFoundError as exc:
                raise HTTPException(
                    404,
                    "Evidence file not found",
                ) from exc

        if (
            len(contents) > MAX_EVIDENCE_BYTES
            or (
                size_bytes is not None
                and size_bytes != len(contents)
            )
            or (
                sha256 is not None
                and not hmac.compare_digest(
                    hashlib.sha256(contents).hexdigest(),
                    sha256,
                )
            )
        ):
            raise HTTPException(
                503,
                "Evidence file failed integrity checks",
            )

        return contents

    def delete(
        self,
        *,
        storage_backend: str,
        file_path: str,
    ) -> None:
        if storage_backend != self.mode:
            raise RuntimeError(
                "Evidence storage configuration mismatch"
            )

        if self.mode == "s3":
            self._client().delete_object(
                Bucket=self.bucket,
                Key=self._key(file_path),
            )

        else:
            self._local_path(file_path).unlink(missing_ok=True)