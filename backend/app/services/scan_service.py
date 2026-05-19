#type: ignore
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.scan_repo import ScanRepository
from app.schemas.scan import InitiateScanRequest

logger = logging.getLogger(__name__)

class ScanService:
    @staticmethod
    async def start_scan(db: Session, scan_data: InitiateScanRequest) -> Any:
        logger.info(f"Initiating CTEM scan for domain: {scan_data.domain}")

        #repo creates a new record in the db
        scan_record = ScanRepository.create_scan(
            db=db,
            domain=scan_data.domain,
            email=scan_data.email
        )

        #fire off Celery task to the RabbitMQ queue
        try:
            #trigger_osint_scan_task.delay(str(scan_record.id), scan_data.domain)
            logger.info(f"Successfully queued OSINT worker for scan {scan_record.id}")
        except Exception:
            logger.exception("Failed to push task to queue for scan %s", scan_record.id)

        return scan_record
