from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scan import Scan  #type: ignore
from app.models.finding import Finding  #type: ignore


async def get_scan_summary(db: AsyncSession, scan_id: UUID) -> Scan | None:
    """
    Fetches a summary of the scan for the given scan_id.
    This is used by the frontend to display the scan status and progress.
    """
    query = select(Scan).where(Scan.id == scan_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_risk_snapshot(db: AsyncSession, scan_id: UUID) -> dict:
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