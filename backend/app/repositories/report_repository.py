from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.report import Report
from app.models.base import ReportStatus
from app.models.scan import Scan


async def get_report_by_scan_id(db: AsyncSession, scan_id: str) -> Report | None:
    result = await db.execute(
        select(Report).where(Report.scan_id == UUID(scan_id))
    )
    return result.scalar_one_or_none()


async def get_or_create_report(db: AsyncSession, scan_id: str) -> Report:
    report = await get_report_by_scan_id(db, scan_id)

    if report:
        return report

    report = Report(scan_id=UUID(scan_id), status=ReportStatus.PENDING)
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def mark_report_generating(db: AsyncSession, scan_id: str) -> Report:
    report = await get_or_create_report(db, scan_id)
    report.status = ReportStatus.GENERATING
    report.error_message = None

    await db.commit()
    await db.refresh(report)
    return report


async def mark_report_task_queued(
    db: AsyncSession,
    scan_id: str,
    task_id: str,
) -> Report:
    report = await get_or_create_report(db, scan_id)
    report.task_id = task_id
    report.status = ReportStatus.GENERATING
    report.error_message = None

    await db.commit()
    await db.refresh(report)
    return report


async def mark_report_completed(
    db: AsyncSession,
    scan_id: str,
    pdf_path: str,
) -> Report:
    report = await get_or_create_report(db, scan_id)
    report.status = ReportStatus.COMPLETED
    report.pdf_path = pdf_path
    report.generated_at = datetime.now(timezone.utc)
    report.error_message = None

    await db.commit()
    await db.refresh(report)
    return report


async def mark_report_failed(
    db: AsyncSession,
    scan_id: str,
    error_message: str,
) -> Report:
    report = await get_or_create_report(db, scan_id)
    report.status = ReportStatus.FAILED
    report.error_message = error_message

    await db.commit()
    await db.refresh(report)
    return report


async def load_report_data(db: AsyncSession, scan_id: str) -> dict[str, Any]:
    result = await db.execute(
        select(Scan)
        .options(
            selectinload(Scan.findings),
            selectinload(Scan.sources),
        )
        .where(Scan.id == UUID(scan_id))
    )

    scan = result.scalar_one_or_none()

    if scan is None:
        raise ValueError(f"Scan not found: {scan_id}")

    return {
        "scan": scan,
        "findings": scan.findings,
        "scan_sources": scan.sources,
        "report": await get_or_create_report(db, scan_id),
    }