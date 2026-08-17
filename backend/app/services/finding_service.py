from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import Finding
from app.repositories.audit_repository import AuditRepository
from app.repositories.engagement_repository import EngagementRepository
from app.repositories.finding_repository import FindingRepository
from app.schemas.finding import EvidenceFileResponse, FindingDetail, FindingUpdate


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
            review_status=finding.review_status,
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
    async def update_finding(
        db: AsyncSession,
        finding_id: UUID,
        user_id: UUID,
        request: FindingUpdate,
    ) -> FindingDetail:
        finding = await FindingService.require_finding_access(
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
    async def register_evidence(
        db: AsyncSession,
        *,
        finding_id: UUID,
        user_id: UUID,
        file_name: str,
        file_path: str,
        mime_type: str | None,
    ) -> EvidenceFileResponse:
        finding = await FindingService.require_finding_access(
            db,
            finding_id=finding_id,
            user_id=user_id,
        )

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
                "file_name": file_name,
            },
        )

        await db.refresh(evidence)

        return EvidenceFileResponse.model_validate(evidence)