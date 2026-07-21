import builtins
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.base import ScanStatus, Severity
from app.models.finding import Finding
from app.models.report import Report
from app.models.scan import Scan
from app.models.scan_source import ScanSource, ScanSourceStatus

logger = logging.getLogger(__name__)

# This could easily change
TOTAL_SCAN_SOURCES = ["dns", "urlscan", "wappalyzer", "crt.sh", "shodan", "hunter.io", "hibp"]

class ScanRepository:

    @staticmethod
    async def create_scan(
        db: AsyncSession,
        domain: str,
        email: str | None = None,
        user_id: UUID | None = None,
    ) -> Scan:
        """Creates a new pending scan record in the database."""
        try:
            new_scan = Scan(
                domain=domain,
                email=email,
                user_id=user_id,
            )
            db.add(new_scan)
            await db.commit()
            await db.refresh(new_scan)
            return new_scan
        except SQLAlchemyError:
            await db.rollback()
            logger.exception("Failed to create scan for domain %s", domain)
            raise

    @staticmethod
    async def get_scan_by_id(db: AsyncSession, scan_id: UUID) -> Scan | None:
        """Retrieves a scan and its associated assets/findings."""
        query = select(Scan).where(Scan.id == scan_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()


    @staticmethod
    async def list_scans(db: AsyncSession, user_id: UUID) -> list[dict[str, Any]]:
        query = (
            select(
                Scan,
                func.count(Finding.id).label("total_findings"),
                func.sum(case((Finding.severity == Severity.CRITICAL, 1), else_=0))
                .label("critical_count"),
                func.sum(case((Finding.severity == Severity.HIGH, 1), else_=0))
                .label("high_count"),
                func.sum(case((Finding.severity == Severity.MEDIUM, 1), else_=0))
                .label("medium_count"),
                func.sum(case((Finding.severity == Severity.LOW, 1), else_=0)).label("low_count"),
            )
            .outerjoin(Finding, Finding.scan_id == Scan.id)
            .where(Scan.user_id == user_id)
            .group_by(Scan.id)
            .order_by(Scan.created_at.desc())
        )

        if status:
            query = query.where(Scan.status == status)

        query = query.limit(limit)

        rows = (await db.execute(query)).all()
        return [
            {
                "id": row.Scan.id,
                "domain": row.Scan.domain,
                "created_at": row.Scan.created_at,
                "status": row.Scan.status,
                "total_findings": int(row.total_findings or 0),
                "critical_count": int(row.critical_count or 0),
                "high_count": int(row.high_count or 0),
                "medium_count": int(row.medium_count or 0),
                "low_count": int(row.low_count or 0),
            }
            for row in rows
        ]

    @staticmethod
    async def mark_scan_failed(db: AsyncSession, scan_id: UUID, error_message: str, is_partial: bool = False) -> Scan: # noqa: E501
        """
        Update scan's status to failed or partial and logs the exact error, for frontend display
        """
        scan = await ScanRepository.get_scan_by_id(db, scan_id)
        if not scan:
            raise ValueError(f"Scan {scan_id} not found.")

        scan.status = ScanStatus.PARTIAL if is_partial else ScanStatus.FAILED
        scan.error_message = error_message

        await db.commit()
        await db.refresh(scan)
        return scan


    @staticmethod
    async def save_source_result(
        db: AsyncSession,
        scan_id: UUID,
        source_name: str,
        payload: dict[str, Any],
    ) -> Scan:
        
        scan = await ScanRepository.get_scan_by_id(db, scan_id)

        if not scan:
            raise ValueError(f"Scan {scan_id} not found.")
        
        try:
            source_status = payload["status"]
            source_query = select(ScanSource).where(
                ScanSource.scan_id == scan.id,
                ScanSource.source_name == source_name,
            )
            source_result = await db.execute(source_query)
            scan_source = source_result.scalar_one_or_none()

            if scan_source:
                scan_source.status = ScanSourceStatus(source_status)
                scan_source.raw_result = payload.get("raw_result")
                scan_source.error_message = payload.get("error_message")
            else:
                scan_source = ScanSource(
                    scan_id=scan.id,
                    source_name=source_name,
                    status=ScanSourceStatus(source_status),
                    raw_result=payload.get("raw_result"),
                    error_message=payload.get("error_message"),
                )
                db.add(scan_source)

            for asset_data in payload.get("assets", []):
                identifier = asset_data.get("identifier")
                if not identifier:
                    continue

                asset = Asset(
                    scan_id=scan.id,
                    identifier=identifier,
                    asset_type=asset_data.get("asset_type", "unknown"),
                )
                db.add(asset)

            for finding_data in payload.get("findings", []):
                finding = Finding(
                    scan_id=scan.id,
                    source=finding_data.get("source", source_name),
                    severity=Severity(finding_data.get("severity", "info")),
                    title=finding_data.get("title", "Untitled finding"),
                    description=finding_data.get("description"),
                    recommendation=finding_data.get("recommendation"),
                    evidence=finding_data.get("evidence"),
                )
                db.add(finding)
            
            await db.flush()

            source_status_results = await db.execute(
                select(ScanSource.source_name, 
                       ScanSource.status).where(ScanSource.scan_id == scan.id)
            )

            source_statuses = source_status_results.all()
            total_sources = len(TOTAL_SCAN_SOURCES)

            finished_statuses = [
                ScanSourceStatus.COMPLETED,
                ScanSourceStatus.FAILED,
                ScanSourceStatus.SKIPPED,
                ScanSourceStatus.PARTIAL,
            ]

            finished_count = sum(
                1 for _, status in source_statuses
                if status in finished_statuses
            )

            progress = int((finished_count / total_sources) * 100)
            min_progress = builtins.min(progress, 100)
            setattr(scan, "progress", min_progress)

            if finished_count == total_sources:
                failed_sources = [
                    source_name for source_name, status in source_statuses
                    if status != ScanSourceStatus.COMPLETED
                ]

                if len(failed_sources) == 0:
                    scan.status = ScanStatus.COMPLETED
                    scan.error_message = None
                elif len(failed_sources) == total_sources:
                    scan.status = ScanStatus.FAILED
                    scan.error_message = "All Scan Sources Failed"
                else:
                    scan.status = ScanStatus.PARTIAL
                    scan.error_message = f"Some Scan Sources Failed: {', '.join(failed_sources)}"
            else:
                scan.status = ScanStatus.RUNNING

            await db.commit()
            await db.refresh(scan)
            return scan
        
        except SQLAlchemyError:
            await db.rollback()
            logger.exception("Failed to save scan source result for scan %s", scan_id)
            raise


    @staticmethod
    async def get_scan_status(db: AsyncSession, scan_id: UUID) -> dict[str, Any] | None:
        scan = await ScanRepository.get_scan_by_id(db, scan_id)

        if not scan:
            return None
        
        source_results = await db.execute(
            select(ScanSource).where(ScanSource.scan_id == scan_id)
        )
        sources = source_results.scalars().all()

        report_result = await db.execute(
            select(Report).where(Report.scan_id == scan_id)
        )
        report = report_result.scalar_one_or_none()

        return {
            "scan_id": str(scan.id),
            "domain": scan.domain,
            "created_at": scan.created_at,
            "status": scan.status.value,
            "progress": scan.progress,
            "sources": [
                {
                    "source_name": source.source_name,
                    "status": source.status.value,
                    "error_message": source.error_message,
                }
                for source in sources
            ],
            "report_status": {
                "status": report.status.value,
                "pdf_path": report.pdf_path,
            } if report else None,
        }

    @staticmethod
    async def update_scan_status(db: AsyncSession, scan_id: UUID, status: ScanStatus) -> None:
        scan = await ScanRepository.get_scan_by_id(db, scan_id)
        if scan:
            scan.status = status
            await db.commit()

    @staticmethod
    async def get_scan_metrics(db: AsyncSession, scan_id: UUID) -> dict[str, Any] | None:
        scan = await ScanRepository.get_scan_by_id(db, scan_id)
        if not scan:
            return None

        findings_stmt = (
            select(Findings.severity, func.count(Finding.id))
            .where(Finding.scan_id == scan_id)
            .group_by(Finding.severity)
        )
        f_rows = (await db.execute(findings_stmt)).all()
        findings_breakdown = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0, "total": 0}
        for sev, count in f_rows:
            key = sev.value.lower() if hasattr(sev, "value") else str(sev).lower()
            if key in findings_breakdown:
                findings_breakdown[key] = count
                findings_breakdown["total"] += count

        assets_stmt = (
            select(Asset.asset_type, func.count(Asset.id))
            .where(Asset.scan_id == scan_id)
            .group_by(Asset.asset_type)
        )
        a_rows = (await db.execute(assets_stmt)).all()
        assets_breakdown = {"total": 0}
        for a_type, count in a_rows:
            assets_breakdown[a_type] = count
            assets_breakdown["total"] += count

        weighted_score = (
            (findings_breakdown["critical"] * 25) +
            (findings_breakdown["high"] * 15) +
            (findings_breakdown["medium"] * 5) +
            (findings_breakdown["low"] * 1)
        )
        risk_score = builtins.min(100, weighted_score)

        return {
            "risk_score": risk_score,
            "risk_level": "HIGH RISK" if risk_score >= 70 else ("MEDIUM RISK" if risk_score >= 40 else "LOW RISK"),
            "findings": findings_breakdown,
            "assets": assets_breakdown,
        }