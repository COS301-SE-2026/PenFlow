from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import FindingReviewStatus, FindingStatus, Severity
from app.models.engagement_asset import EngagementAsset
from app.models.evidence_file import EvidenceFile
from app.models.finding import Finding
from app.schemas.finding import FindingCreate, FindingUpdate


class FindingRepository:
    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        finding_id: UUID,
    ) -> Finding | None:
        query = (
            select(Finding).options(
                selectinload(Finding.evidence_files),
                selectinload(Finding.retests),
            ).where(Finding.id == finding_id)
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()


    @staticmethod
    async def get_for_assigned_engagement(
        db: AsyncSession,
        finding_id: UUID,
        engagement_id: UUID,
    ) -> Finding | None:
        query = (
            select(Finding).options(
                selectinload(Finding.evidence_files),
                selectinload(Finding.retests),
            ).where(
                Finding.id == finding_id,
                Finding.engagement_id == engagement_id,
            )
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()


    @staticmethod
    async def list_by_engagement(
        db: AsyncSession,
        *,
        engagement_id: UUID,
        source: str | None,
        severity: Severity | None,
        finding_status: FindingStatus | None,
        review_status: FindingReviewStatus | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[tuple[Finding, str | None]], int]:
        query = (
            select(
                Finding,
                EngagementAsset.identifier.label("asset_identifier"),
            ).outerjoin(
                EngagementAsset,
                EngagementAsset.id == Finding.engagement_asset_id,
            ).where(Finding.engagement_id == engagement_id)
        )

        count_query = select(func.count(Finding.id)).where(
            Finding.engagement_id == engagement_id
        )

        if source is not None:
            query = query.where(func.lower(Finding.source) == source.lower())
            count_query = count_query.where(func.lower(Finding.source) == source.lower())

        if severity is not None:
            query = query.where(Finding.severity == severity)
            count_query = count_query.where(Finding.severity == severity)

        if finding_status is not None:
            query = query.where(Finding.status == finding_status)
            count_query = count_query.where(Finding.status == finding_status)

        if review_status is not None:
            query = query.where(Finding.review_status == review_status)
            count_query = count_query.where(Finding.review_status == review_status)

        stripped_search = search.strip() if search else None

        if stripped_search:
            search_filter = Finding.title.ilike(f"%{stripped_search}%")
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        query = (
            query.order_by(Finding.created_at.desc(), Finding.id.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(query)
        rows = [(row[0], row.asset_identifier) for row in result.all()]
        total = int(await db.scalar(count_query) or 0)

        return rows, total


    @staticmethod
    async def create_manual_finding(
        db: AsyncSession,
        engagement_id: UUID,
        created_by: UUID,
        request: FindingCreate,
    ) -> Finding:
        finding = Finding(
            engagement_id=engagement_id,
            engagement_asset_id=request.engagement_asset_id,
            source="manual",
            status=FindingStatus.OPEN,
            review_status=FindingReviewStatus.DRAFT,
            severity=request.severity,
            cvss_score=request.cvss_score,
            cve_id=request.cve_id,
            title=request.title,
            description=request.description,
            recommendation=request.recommendation,
            created_by=created_by,
        )

        db.add(finding)
        await db.commit()
        await db.refresh(finding)

        return finding


    @staticmethod
    async def update_finding(
        db: AsyncSession,
        finding: Finding,
        request: FindingUpdate,
    ) -> Finding:
        updates = request.model_dump(exclude_unset=True)

        for field, value in updates.items():
            setattr(finding, field, value)

        await db.commit()
        await db.refresh(finding)

        return finding


    @staticmethod
    async def add_evidence_rec(
        db: AsyncSession,
        *,
        finding_id: UUID,
        uploaded_by: UUID,
        file_name: str,
        file_path: str,
        mime_type: str | None,
    ) -> EvidenceFile:
        evidence = EvidenceFile(
            finding_id=finding_id,
            uploaded_by=uploaded_by,
            file_name=file_name,
            file_path=file_path,
            mime_type=mime_type,
        )

        db.add(evidence)
        await db.commit()
        await db.refresh(evidence)

        return evidence