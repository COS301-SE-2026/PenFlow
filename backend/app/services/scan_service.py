import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.queue.celery_app import celery_app
from app.repositories.domain_repository import DomainRepository
from app.repositories.scan_repo import ScanRepository
from app.schemas.scan import InitiateScanRequest, ScanTypeEnum

logger = logging.getLogger(__name__)


class ScanService:
    @staticmethod
    async def start_scan(
        db: AsyncSession,
        scan_data: InitiateScanRequest,
        user_id: Any | None = None,
    ) -> Any:
        logger.info(
            "Initiating %s scan for domain: %s", scan_data.scan_type.value, scan_data.domain
        )

        if scan_data.scan_type == ScanTypeEnum.ACTIVE_VULNERABILITY:
            if not scan_data.verified_domain_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="verified_domain_id is required for active vulnerability scans.",
                )
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required for active scans.",
                )

            verified_domain = await DomainRepository.get_by_id(
                db, scan_data.verified_domain_id, user_id
            )
            if not verified_domain or verified_domain.status.value != "verified":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only run active scans on a fully verified domain.",
                )

            if verified_domain.domain.lower() != scan_data.domain.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Domain string does not match the verified domain records.",
                )

        # repo creates a new record in the db
        scan_record = await ScanRepository.create_scan(
            db=db,
            domain=scan_data.domain,
            scan_type=scan_data.scan_type.value,
            email=scan_data.email,
            user_id=user_id,
            verified_domain_id=scan_data.verified_domain_id,
        )

        # fire off Celery task to the RabbitMQ queue
        try:
            await ScanService.publish_scan_task(
                db,
                scan_record,
            )

            await db.commit()
            await db.refresh(scan_record)

        except Exception as exc:
            await db.rollback()

            logger.exception("Failed to push task to queue for scan %s", scan_record.id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The scan queue is temporarily unavailable.",
            ) from exc

        return scan_record


    @staticmethod
    async def publish_scan_task(
        db: AsyncSession,
        scan_record: Any,
    ) -> str:
        scan_type = (
            scan_record.scan_type.value
            if hasattr(scan_record.scan_type, "value")
            else str(scan_record.scan_type)
        )

        if scan_type == ScanTypeEnum.ACTIVE_VULNERABILITY.value:
            task_name="scan.phase2_full"

        elif scan_type == ScanTypeEnum.PASSIVE_CTEM.value:
            task_name="scan.full"

        else:
            raise ValueError(
                f"Unsupported scan type: {scan_type}"
            )

        task = celery_app.send_task(
            task_name,
            args=[
                str(scan_record.id),
                scan_record.domain,
            ],
        )

        scan_record.task_id = str(task.id)

        await db.flush()
        logger.info(
            "Queued %s task %s for scan %s",
            scan_type,
            task.id,
            scan_record.id,
        )

        return str(task.id)