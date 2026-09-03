from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.engagement import Engagement
from app.models.finding import Finding
from app.models.report import Report


async def build_phase3_report_context(
        db: AsyncSession, engagement_id: str | UUID, version: int = 1
) -> dict[str, Any]:
    eng_uuid = UUID(str(engagement_id)) if isinstance(engagement_id, str) else engagement_id 

    result = await db.execute(
        select(Engagement)
        .options(
            selectinload(Engagement.assets),
            selectinload(Engagement.findings).selectinload(Finding.evidence_files),
            selectinload(Engagement.findings).selectinload(Finding.retests),
        )
        .where(Engagement.id == eng_uuid)
    )
    engagement = result.scalar_one_or_none()

    if not engagement:
        raise ValueError(f"Engagement not found: {eng_uuid}")

    report_result = await db.execute(
        select(Report).where(
            Report.engagement_id == eng_uuid,
            Report.version == version 
        )
    )
    report = report_result.scalar_one_or_none()

    findings = engagement.findings or []
    severity_counts = {
        "critical": sum(1 for f in findings if f.severity == "critical"),
        "high": sum(1 for f in findings if f.severity == "high"),
        "medium": sum(1 for f in findings if f.severity == "medium"),
        "low": sum(1 for f in findings if f.severity == "low"),
        "info": sum(1 for f in findings if f.severity == "info"),
    }
    total_findings = len(findings)

    return {
        "engagement": engagement,
        "client": engagement.primary_contact or "Valued Client",
        "engagement_title": engagement.title,
        "engagement_type": engagement.engagement_type,
        "assessment_type": engagement.assessment_type,
        "scope": engagement.scope,
        "objective": engagement.objective,
        "constraints": engagement.constraints,
        "assets": engagement.assets,
        "findings": findings,
        "severity_counts": severity_counts,
        "total_findings": total_findings,
        "report_version": version,
        "generated_at": report.generated_at if report else None,
    }