from sqlalchemy.orm import Session
import logging
from app.schemas.scan import InitiateScanRequest,ScanStatus
from app.repositories.scan_repo import ScanRepository
#from app.queue.producer import trigger_osint_scan_task

logger = logging.getLogger(__name__)

class ScanService:
    @staticmethod
    async def start_scan(db: Session, scan_date: InitaiteScanRequest):
        logger.info(f"Initiating CTEM scan for domain: {scan_data.domain}")

        #repo creates a new record in the db
        scan_record = ScanRepository.create_scan(
            db=db,
            domain=scan_data.domain
            email=scan_data.email
        )

        #fire off Celery task to the RabbitMQ queue
        try:
            #trigger_osint_scan_task.delay(str(scan_record.id), scan_data.domain)
            logger.info(f"Successfully queued OSINT worker for scan {scan_record.id}")
        except Exception as e:
            logger.error(f"Failed to push task to queue for scan {scan_record.id}: {e}")

        return scan_record

        pass