import logging
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.base import ScanStatus, Severity
from app.models.finding import Finding
from app.models.scan import Scan
from app.models.scan_source import ScanSource, ScanSourceStatus

logger = logging.getLogger(__name__)

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
    async def save_normalized_results(
        db: AsyncSession, 
        scan_id: UUID, 
        results: dict[str, Any],
        ) -> Scan:
        """
        Takes the normalized JSON contract from the Celery worker and 
        translates it into Asset and Finding database records.
        """
        scan = await ScanRepository.get_scan_by_id(db, scan_id)
        if not scan:
            raise ValueError(f"Scan {scan_id} not found.")

        try:
            findings_data = results.get("normalized_findings", {})

            #parse subdomain into assets
            attack_surface = findings_data.get("attack_surface", {})
            for sub in attack_surface.get("subdomains",[]):
                asset = Asset(scan_id=scan.id, identifier=sub, asset_type="Subdomain")
                db.add(asset)
            
            #parse IP addresses into assets
            infrastructure = findings_data.get("infrastructure", {})
            for ip in infrastructure.get("ip_addresses", []):
                asset = Asset(scan_id=scan.id, identifier=ip, asset_type="IP Address")
                db.add(asset)

            #parse breaches into findings
            identity = findings_data.get("identity_exposure", {})
            for breach in identity.get("know_breaches", []):
                finding = Finding(
                    scan_id=scan.id,
                    source="HaveIBeenPwned",
                    severity=Severity.HIGH,
                    title=f"Data Breach: {breach.get('breach_name')}",
                    description=f"Breach occurred on {breach.get('date')}.",
                    evidence={"leaked_data": breach.get("data_leaked")}
                )
                db.add(finding)

            for email in identity.get("public_emails_found",[]):
                finding = Finding(
                    scan_id=scan.id,
                    source="Hunter.io",
                    severity=Severity.MEDIUM if email.get("type") == "personal" else Severity.LOW,
                    title=f"Exposed Email: {email.get('email')}",
                    evidence={"confidence": email.get("confidence"), "type": email.get("type")}
                )
                db.add(finding)

            scan.status = ScanStatus.COMPLETED
            scan.progress = 100
            await db.commit()
            await db.refresh(scan)
            return scan

        except SQLAlchemyError:
            await db.rollback()
            logger.exception("Failed to save scan for domain %s", scan_id)
            raise

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
    async def save_worker_results(
        db: AsyncSession,
        scan_id: UUID,
        results: dict[str, Any],
    ) -> Scan:
        scan = await ScanRepository.get_scan_by_id(db, scan_id)

        if not scan:
            raise ValueError(f"Scan {scan_id} not found.")

        try:
            subtasks = results.get("subtasks", [])

            for subtask in subtasks:
                source_name = subtask.get("source_name", "unknown")
                source_status = subtask.get("status", "failed")

                logger.info(
                    "Source %s has %s assets and %s findings",
                    source_name,
                    len(subtask.get("assets", [])),
                    len(subtask.get("findings", [])),
                )

                scan_source = ScanSource(
                    scan_id=scan.id,
                    source_name=source_name,
                    status=ScanSourceStatus(source_status),
                    raw_result=subtask.get("raw_result"),
                    error_message=subtask.get("error_message"),
                )
                db.add(scan_source)

                for asset_data in subtask.get("assets", []):
                    identifier = asset_data.get("identifier")

                    if not identifier:
                        continue

                    asset = Asset(
                        scan_id=scan.id,
                        identifier=identifier,
                        asset_type=asset_data.get("asset_type", "unknown"),
                    )
                    db.add(asset)

                for finding_data in subtask.get("findings", []):
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

            scan.progress = 100
            scan.status = ScanStatus.COMPLETED

            await db.commit()
            await db.refresh(scan)
            return scan

        except SQLAlchemyError:
            await db.rollback()
            logger.exception("Failed to save worker results for scan %s", scan_id)
            raise