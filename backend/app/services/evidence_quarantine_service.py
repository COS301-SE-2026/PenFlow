import hashlib
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.models.evidence_file import EvidenceFile
from app.models.finding import Finding
from app.repositories.audit_repository import AuditRepository
from app.schemas.finding import EvidenceFileResponse
from app.services.evidence_storage_service import EvidenceStorageService
from app.services.malware_service import scan_bytes
from app.services.service_delivery_service import ServiceDeliveryService
from app.utils.audit_transaction import audited_operation

logger = logging.getLogger(__name__)


def require_clean(evidence: EvidenceFile) -> None:
    if evidence.quarantine_status != "clean":
        raise HTTPException(
            423,
            "Evidence is quarantined until its security check passes",
        )

    if (
        not evidence.sha256
        or evidence.size_bytes is None
        or evidence.scanned_at is None
    ):
        raise HTTPException(
            423,
            "Evidence has no completed security check",
        )


class EvidenceQuarantineService:
    @staticmethod
    async def process_one(db: AsyncSession) -> bool:
        now = datetime.now(timezone.utc)

        try:
            evidence = await db.scalar(
                select(EvidenceFile).join(
                    Finding,
                    Finding.id == EvidenceFile.finding_id,
                ).where(
                    Finding.engagement_id.is_not(None),
                    EvidenceFile.quarantine_status == "pending",
                    EvidenceFile.next_scan_at <= now,
                ).order_by(
                    EvidenceFile.next_scan_at,
                    EvidenceFile.id,
                ).limit(1).with_for_update(
                    of=EvidenceFile,
                    skip_locked=True,
                )
            )

            if evidence is None:
                await db.rollback()
                return False

            finding = await db.get(
                Finding,
                evidence.finding_id,
            )

            evidence.scan_attempts += 1
            evidence.scanned_at = None
            evidence.scanner_version = None

            try:
                storage = EvidenceStorageService()

                contents = await run_in_threadpool(
                    storage.read,
                    storage_backend=evidence.storage_backend,
                    file_path=evidence.file_path,
                    sha256=evidence.sha256,
                    size_bytes=evidence.size_bytes,
                )

                verdict = await run_in_threadpool(
                    scan_bytes,
                    contents,
                )

                if verdict.status not in {"clean", "rejected"}:
                    raise RuntimeError(
                        "Invalid antivirus verdict"
                    )

                evidence.sha256 = hashlib.sha256(
                    contents
                ).hexdigest()
                evidence.size_bytes = len(contents)
                evidence.quarantine_status = verdict.status
                evidence.scan_message = verdict.message
                evidence.scanner_version = verdict.scanner_version
                evidence.scanned_at = datetime.now(timezone.utc)

            except Exception:
                logger.exception(
                    "Evidence security check failed: %s",
                    evidence.id,
                )

                evidence.quarantine_status = (
                    "failed"
                    if evidence.scan_attempts >= 3
                    else "pending"
                )

                evidence.scan_message = (
                    "Security check failed; service delivery can retry"
                    if evidence.quarantine_status == "failed"
                    else "Security check unavailable; automatic retry pending"
                )

                evidence.next_scan_at = (
                    datetime.now(timezone.utc)
                    + timedelta(minutes=5)
                )

            if evidence.quarantine_status != "pending":
                await AuditRepository.create_log(
                    db,
                    user_id=None,
                    commit=False,
                    action=(
                        "evidence.quarantine_"
                        f"{evidence.quarantine_status}"
                    ),
                    entity_type="evidence_file",
                    entity_id=evidence.id,
                    metadata={
                        "engagement_id": str(
                            finding.engagement_id
                        ),
                        "finding_id": str(finding.id),
                        "attempts": evidence.scan_attempts,
                    },
                )

            await db.commit()
            return True

        except BaseException:
            await db.rollback()
            raise


    @staticmethod
    @audited_operation
    async def retry(
        db: AsyncSession,
        *,
        evidence_id: UUID,
        user_id: UUID,
    ) -> EvidenceFileResponse:
        evidence = await db.scalar(
            select(EvidenceFile).where(
                EvidenceFile.id == evidence_id
            ).with_for_update()
        )

        if evidence is None:
            raise HTTPException(404, "Evidence not found")

        finding = await db.get(
            Finding,
            evidence.finding_id,
        )

        if finding is None or finding.engagement_id is None:
            raise HTTPException(404, "Evidence not found")

        await ServiceDeliveryService.require_owned_engagement(
            db,
            engagement_id=finding.engagement_id,
            service_delivery_id=user_id,
        )

        if evidence.quarantine_status != "failed":
            raise HTTPException(
                409,
                "Only failed security checks can be retried",
            )

        evidence.quarantine_status = "pending"
        evidence.scan_attempts = 0
        evidence.scan_message = None
        evidence.scanned_at = None
        evidence.scanner_version = None
        evidence.next_scan_at = datetime.now(timezone.utc)

        await AuditRepository.create_log(
            db,
            user_id=user_id,
            action="evidence.quarantine_retry_requested",
            entity_type="evidence_file",
            entity_id=evidence.id,
            metadata={
                "engagement_id": str(finding.engagement_id),
                "finding_id": str(finding.id),
            },
        )

        return EvidenceFileResponse.model_validate(evidence)