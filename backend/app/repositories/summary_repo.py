from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.asset import Asset
from app.models.finding import Finding
from app.models.report import Report
from app.models.scan import Scan
from app.models.scan_source import ScanSource


async def get_scan_summary(db: AsyncSession, scan_id: UUID) -> Scan | None:
    """
    Fetches a summary of the scan for the given scan_id.
    This is used by the frontend to display the scan status and progress.
    """
    query = select(Scan).where(Scan.id == scan_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_risk_snapshot(db: AsyncSession, scan_id: UUID) -> dict[str, Any]:
    """
    Fetches a risk snapshot for the given scan_id.
    This aggregates findings by severity to give a quick overview of the scan's risk profile.
    """
    query = (
        select(Finding.severity, func.count(Finding.id))
        .where(Finding.scan_id == scan_id)
        .group_by(Finding.severity)
    )
    result = await db.execute(query)
    counts = result.all()

    snapshot = {
        "total_findings": 0,
        "critical_count": 0,
        "high_count": 0,
        "medium_count": 0,
        "low_count": 0,
        "info_count": 0
    }

    for severity, count in counts:

        sev_str = severity.value if hasattr(severity, "value") else str(severity).lower()

        key = f"{sev_str}_count"
        
        if key in snapshot:
            snapshot[key] = count
            snapshot["total_findings"] += count

    return snapshot

async def get_top_findings_preview(
    db: AsyncSession, 
    scan_id: UUID, 
    limit: int = 5,
    ) -> list[dict[str, Any]]:

    """
    Fetches highest severity findings, join resolved assets
    as well as truncates long test fields for a UI preview.
    """
    query = (
        select(Finding, Asset)
        .outerjoin(Asset, Finding.asset_id == Asset.id)
        .where(Finding.scan_id == scan_id)
        .order_by(Finding.severity.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.all()

    previews = []
    for finding, asset in rows:
        desc_snippet = finding.description
        if desc_snippet and len(desc_snippet) >  120:
            desc_snippet = desc_snippet[:120] + "..."

        recc_snippet = finding.recommendation
        if recc_snippet and len(recc_snippet) >  120:
            recc_snippet = recc_snippet[:120] + "..."

        

        previews.append({
            "id": finding.id,
            "severity": finding.severity,
            "title": finding.title,
            "description": desc_snippet,
            "recommendation": recc_snippet,
            "source": finding.source,
            "asset_identifier": asset.identifier if asset else None,
            "asset_type": asset.asset_type if asset else None,
            "created_at": finding.created_at
        })

    return previews

async def get_asset_impact_summary(db: AsyncSession, scan_id: UUID) -> dict[str, Any]:
    """
    Fetches an impact summary for the given scan_id.
    This aggregates asset-related information to give a quick overview of the scan's impact.
    """
    query = (
        select(Asset)
        .options(selectinload(Asset.findings))
        .where(Asset.scan_id == scan_id)
    )
    result = await db.execute(query)
    assets = result.scalars().all()

    total_assets = len(assets)
    affected_assets = 0
    breakdown_dict: dict[str, dict[str, Any]] = {}
    top_assets = []

    severity_rank = {"info": 1, "low": 2, "medium": 3, "high": 4, "critical": 5}

    for asset in assets:
        finding_count = len(asset.findings)
        is_affected = finding_count > 0

        if is_affected:
            affected_assets += 1

        a_type = asset.asset_type
        if a_type not in breakdown_dict:
            breakdown_dict[a_type] = {
                "asset_type": a_type,
                "total_assets": 0,
                "affected_assets": 0
            }
        breakdown_dict[a_type]["total_assets"] += 1
        if is_affected:
            breakdown_dict[a_type]["affected_assets"] += 1

        if is_affected:
            highest_finding = max(
                asset.findings,
                key=lambda f: severity_rank.get(
                    f.severity.value if hasattr(f.severity, 'value')
                    else str(f.severity).lower(), 0
                )
            )
            top_assets.append({
                "identifier": asset.identifier,
                "asset_type": asset.asset_type,
                "finding_count": finding_count,
                "highest_severity": highest_finding.severity
            })

    top_assets.sort(
        key=lambda x: (
            severity_rank.get(
                x["highest_severity"].value if hasattr(x["highest_severity"], 'value')
                else str(x["highest_severity"]).lower(), 0
            ),
            x["finding_count"]
        ),
        reverse=True
    )

    return {
        "total_assets_scanned": total_assets,
        "affected_assets_count": affected_assets,
        "asset_type_breakdown": list(breakdown_dict.values()),
        "top_affected_assets": top_assets[:5]
    }

async def get_source_coverage(db: AsyncSession, scan_id: UUID) -> dict[str, Any]:
    """
    Fetches all execution sources for a scan and computes the aggregate
    completion statuses
    """
    query = select(ScanSource).where(ScanSource.scan_id == scan_id)
    result =await db.execute(query)
    sources = result.scalars().all()

    aggregate = {
        "sources_total": len(sources),
        "sources_completed": 0,
        "sources_failed": 0,
        "sources_partial": 0,
        "sources_skipped": 0    
    }

    for source in sources:
        status_str = source.status.value if hasattr(source.status, "value") else str(source.status)
        status_str = status_str.lower()

        if status_str == "completed":
            aggregate["sources_completed"] += 1
        elif status_str == "failed":
            aggregate["sources_failed"] += 1
        elif status_str == "partial":
            aggregate["sources_partial"] += 1
        elif status_str == "skipped":
            aggregate["sources_skipped"] += 1

    return {
        "aggregate": aggregate,
        "sources": sources
    }            
    
async def get_report_status(db: AsyncSession, scan_id: UUID) -> Report | None:
    """
    Fetches the current async pdf generation status for a scan
    None if a report is not created or queued
    """
    query = select(Report).where(Report.scan_id == scan_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()