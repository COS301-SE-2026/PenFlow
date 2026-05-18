#type: ignore
import logging
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.base import ScanStatus, Severity
from app.models.finding import Finding
from app.models.scan import Scan

logger = logging.getLogger(__name__)

class ScanRepository:

    @staticmethod
    def create_scan(db: Session, domain: str, email: str | None = None) -> Scan:
        """Creates a new pending scan record in the database."""
        try:
            new_scan = Scan(
                domain=domain,
                email=email,
                status=ScanStatus.QUEUED,
                progress=0
            )
            db.add(new_scan)
            db.commit()
            db.refresh(new_scan)
            return new_scan
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Failed to create scan for domain {domain}: {e}")
            raise

    @staticmethod
    def get_scan_by_id(db: Session, scan_id: UUID) -> Scan | None:
        """Retrieves a scan and its associated assets/findings."""
        return db.query(Scan).filter(Scan.id == scan_id).first()

    @staticmethod
    def save_normalized_results(db: Session, scan_id: UUID, results: dict) -> Scan:
        """
        Takes the normalized JSON contract from the Celery worker and 
        translates it into Asset and Finding database records.
        """
        scan = ScanRepository.get_scan_by_id(db, scan_id)
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
            db.commit()
            db.refresh(scan)
            return scan

        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Failed to save results for scan {scan_id}: {e}")
            raise

    @staticmethod
    def mark_scan_failed(db: Session, scan_id: UUID, error_message: str, is_partial: bool = False) ->Scan:
        """
        Update scan's status to failed or partial and logs the exact error, for frontend display
        """
        scan = ScanRepository.get_scan_by_id(db, scan_id)
        if not scan:
            raise ValueError(f"Scan {scan_id} not found.")

        scan.status = ScanStatus.PARTIAL if is_partial else ScanStatus.FAILED
        scan.error_message = error_message

        db.commit()
        db.refresh(scan)
        return scan