import logging
from functools import partial
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.models.base import EngagementStatus, FindingStatus, RetestStatus
from app.models.finding import Finding
from app.repositories.audit_repository import AuditRepository
from app.repositories.engagement_repository import EngagementRepository
from app.repositories.finding_repository import FindingRepository
from app.repositories.retest_repository import RetestRepository
from app.schemas.finding import EvidenceFileResponse, FindingDetail, FindingUpdate
from app.services.evidence_storage_service import EvidenceStorageService
from app.services.retest_policy import require_retest_window
from app.utils.audit_transaction import after_commit, audited_operation

logger = logging.getLogger(__name__)

async def remove_evidence_objects(
    references: list[tuple[str, str]],
) -> None:
    for storage_backend, file_path in references:
        try:
            storage = EvidenceStorageService()

            await run_in_threadpool(
                storage.delete,
                storage_backend=storage_backend,
                file_path=file_path,
            )

        except Exception:
            logger.exception(
                "Evidence deletion failed; reconciliation is required"
            )

class FindingService:
    @staticmethod
    async def require_finding_access(
        db: AsyncSession,
        finding_id: UUID,
        user_id: UUID,
    ) -> Finding:
        finding = await FindingRepository.get_by_id(
            db,
            finding_id=finding_id,
        )

        if finding is None or finding.engagement_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Finding was not found.",
            )

        engagement = await EngagementRepository.get_assigned_by_id(
            db,
            engagement_id=finding.engagement_id,
            user_id=user_id,
        )

        if engagement is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Finding was not found.",
            )

        return finding


    @staticmethod
    async def require_editable_finding(
        db: AsyncSession,
        finding_id: UUID,
        user_id: UUID,
    ) -> Finding:
        finding = await FindingService.require_finding_access(
            db, 
            finding_id=finding_id,
            user_id=user_id,
        )

        if finding.engagement_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Finding is not associated with engagement.",
            )

        engagement = await EngagementRepository.get_by_id(
            db,
            engagement_id=finding.engagement_id,
        )

        if engagement is None or engagement.status != EngagementStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Findings can only be modified while the engagement is in progress.",
            )

        return finding


    @staticmethod
    async def get_finding(
        db: AsyncSession,
        finding_id: UUID,
        user_id: UUID,
    ) -> FindingDetail:
        finding = await FindingService.require_finding_access(
            db,
            finding_id=finding_id,
            user_id=user_id,
        )

        asset_identifier = None

        engagement_id = finding.engagement_id

        if engagement_id is None:
             raise HTTPException(
                  status_code=status.HTTP_404_NOT_FOUND,
                  detail="Finding was not found.",
             )

        if finding.engagement_asset_id is not None:
             asset = await EngagementRepository.get_asset_by_id(
                  db,
                  engagement_id=engagement_id,
                  asset_id=finding.engagement_asset_id,
             )

             if asset is not None:
                 asset_identifier = asset.identifier

        return FindingDetail(
            id=finding.id,
            engagement_id=engagement_id,
            engagement_asset_id=finding.engagement_asset_id,
            source=finding.source,
            status=finding.status,
            is_verified=finding.is_verified,
            severity=finding.severity,
            cvss_score=finding.cvss_score,
            cve_id=finding.cve_id,
            title=finding.title,
            description=finding.description,
            recommendation=finding.recommendation,
            created_by=finding.created_by,
            created_at=finding.created_at,
            asset_identifier=asset_identifier,
            evidence_files=[
                EvidenceFileResponse.model_validate(evidence)
                for evidence in finding.evidence_files
            ],
        )


    @staticmethod
    @audited_operation
    async def update_finding(
        db: AsyncSession,
        finding_id: UUID,
        user_id: UUID,
        request: FindingUpdate,
    ) -> FindingDetail:
        finding = await FindingService.require_editable_finding(
            db,
            finding_id=finding_id,
            user_id=user_id,
        )

        engagement_id = finding.engagement_id

        if engagement_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Finding was not found."
            )

        if request.status == FindingStatus.FALSE_POSITIVE and finding.is_verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A verified finding cannot be marked as a false positive.",
            )

        if request.engagement_asset_id is not None:
            asset = await EngagementRepository.get_asset_by_id(
                db,
                engagement_id=engagement_id,
                asset_id=request.engagement_asset_id,
            )

            if asset is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="The selected asset does not belong to this engagement.",   
                )

        changed_fields = list(request.model_dump(exclude_unset=True).keys())

        finding = await FindingRepository.update_finding(
            db,
            finding=finding,
            request=request,
        )

        await AuditRepository.create_log(
            db,
            user_id=user_id,
            action="finding.updated",
            entity_type="finding",
            entity_id=finding.id,
            metadata={
                "engagement_id": str(finding.engagement_id),
                "changed_fields": changed_fields,
            },
        )

        await db.refresh(finding)

        return await FindingService.get_finding(
            db,
            finding_id=finding.id,
            user_id=user_id,
        )


    @staticmethod
    async def require_evidence_upload_access(
        db: AsyncSession,
        *,
        finding_id: UUID,
        user_id: UUID,
        retest_id: UUID | None = None,
    ) -> Finding:
        if retest_id is None:
            return await FindingService.require_editable_finding(
                db,
                finding_id=finding_id,
                user_id=user_id,
            )

        finding = await FindingService.require_finding_access(
            db,
            finding_id=finding_id,
            user_id=user_id,
        )

        retest = await RetestRepository.get_by_id(
            db,
            retest_id=retest_id,
        )

        if retest is None or retest.finding_id != finding.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Retest was not found.",
            )

        engagement_id = finding.engagement_id
        if engagement_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Retest was not found.",
            )

        engagement = await EngagementRepository.get_assigned_by_id(
            db,
            engagement_id=engagement_id,
            user_id=user_id,
        )

        if engagement is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Retest was not found.",
            )

        if (
            engagement.status != EngagementStatus.RETESTING
            or retest.status != RetestStatus.IN_PROGRESS
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Evidence can only be added to an in-progress retest.",
            )

        require_retest_window(engagement.scheduled_end_date)
        return finding
    

    @staticmethod
    @audited_operation
    async def register_evidence(
        db: AsyncSession,
        *,
        finding_id: UUID,
        user_id: UUID,
        file_name: str,
        file_path: str,
        storage_backend: str = "local",
        sha256: str | None = None,
        size_bytes: int | None = None,
        mime_type: str | None,
        retest_id: UUID | None = None,
    ) -> EvidenceFileResponse:
        finding = await FindingService.require_evidence_upload_access(
            db,
            finding_id=finding_id,
            user_id=user_id,
            retest_id=retest_id,
        )

        if retest_id is not None:
            prefix = f"retest-{retest_id}-"
            file_name = prefix + file_name[:255 - len(prefix)]

        engagement_id = finding.engagement_id
        current_finding_id = finding.id

        if engagement_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Finding was not found."
            )

        evidence = await FindingRepository.add_evidence_rec(
            db,
            finding_id=current_finding_id,
            uploaded_by=user_id,
            file_name=file_name,
            file_path=file_path,
            storage_backend=storage_backend,
            sha256=sha256,
            size_bytes=size_bytes,
            mime_type=mime_type,
        )

        evidence_id = evidence.id

        await AuditRepository.create_log(
            db,
            user_id=user_id,
            action="finding.evidence_uploaded",
            entity_type="evidence_file",
            entity_id=evidence_id,
            metadata={
                "engagement_id": str(engagement_id),
                "finding_id": str(current_finding_id),
                "retest_id": str(retest_id) if retest_id else None,
            },
        )

        await db.refresh(evidence)

        return EvidenceFileResponse.model_validate(evidence)


    @staticmethod
    @audited_operation
    async def delete_manual_finding(
        db: AsyncSession,
        finding_id: UUID,
        user_id: UUID,
    ) -> None:
        finding = await FindingService.require_editable_finding(
            db,
            finding_id=finding_id,
            user_id=user_id,
        )

        if finding.source != "manual":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Automated findings cannot be deleted.",
            )

        engagement_id = finding.engagement_id

        evidence_references = [
            (evidence.storage_backend, evidence.file_path)
            for evidence in finding.evidence_files
        ]

        await FindingRepository.delete_finding(
            db,
            finding=finding,
        )

        await AuditRepository.create_log(
            db,
            user_id=user_id,
            action="finding.deleted",
            entity_type="finding",
            entity_id=finding_id,
            metadata={
                "engagement_id": str(engagement_id),
                "source": "manual",
            },
        )

        if evidence_references:
            await after_commit(
                db,
                partial(remove_evidence_objects, evidence_references),
            )


    @staticmethod
    @audited_operation
    async def verify_automated_finding(
        db: AsyncSession,
        finding_id: UUID,
        user_id: UUID,
    ) -> FindingDetail:
        finding = await FindingService.require_editable_finding(
            db,
            finding_id=finding_id,
            user_id=user_id,
        )

        if finding.source == "manual":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Manual findings do not require verification.",
            )

        if finding.is_verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Finding has already been verified.",
            )

        if finding.status == FindingStatus.FALSE_POSITIVE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A false positive cannot be verified.",
            )

        finding = await FindingRepository.mark_verified(
            db,
            finding=finding,
        )

        current_finding_id = finding.id
        engagement_id = finding.engagement_id
        finding_source = finding.source

        await AuditRepository.create_log(
            db,
            user_id=user_id,
            action="finding.verified",
            entity_type="finding",
            entity_id=current_finding_id,
            metadata={
                "engagement_id": str(engagement_id),
                "source": finding_source,
            },
        )

        return await FindingService.get_finding(
            db,
            finding_id=current_finding_id,
            user_id=user_id,
        )
        