import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.queue.celery_app import celery_app
from app.repositories.scan_repo import ScanRepository  #type: ignore
from app.schemas.scan import InitiateScanRequest

logger = logging.getLogger(__name__)

class ScanService:
    @staticmethod
    async def start_scan(db: AsyncSession, scan_data: InitiateScanRequest) -> Any:
        logger.info("Initiating CTEM scan for domain: %s", scan_data.domain)

        #repo creates a new record in the db
        scan_record = await ScanRepository.create_scan(
            db=db,
            domain=scan_data.domain,
            email=scan_data.email
        )

        #fire off Celery task to the RabbitMQ queue
        try:
            task = celery_app.send_task(
                "scan.full",
                args=[str(scan_record.id), scan_data.domain],
            )
            logger.info("Queued OSINT worker task %s for scan %s", task.id, scan_record.id)
        except Exception:
            logger.exception("Failed to push task to queue for scan %s", scan_record.id)

        return scan_record
