from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.scan import Scan

async def get_scan_summary(db: AsyncSession, scan_id: UUID) -> Scan | None:
    """
    Fetches a summary of the scan for the given scan_id.
    This is used by the frontend to display the scan status and progress.
    """
    query = select(Scan).where(Scan.id == scan_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()