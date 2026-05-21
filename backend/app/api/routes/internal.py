import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.base import ScanStatus, Severity
from app.models.finding import Finding
from app.models.scan_source import ScanSource, ScanSourceStatus
from app.repositories.report_repository import mark_report_completed, mark_report_failed
from app.repositories.scan_repo import ScanRepository
from app.schemas.report import ReportCallbackRequest
from app.schemas.scan import ScanCallbackRequest
from app.services.report_service import queue_report_generation
from app.utils.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["Internal Webhooks"])


async def save_scan_callback_results(
    db: AsyncSession,
    scan_id: UUID,
    results: dict[str, Any],
) -> None:
    for subtask in results.get("subtasks", []):
        source_name = subtask.get("source_name", "unknown")
        source_status = subtask.get("status", "failed")

        db.add(
            ScanSource(
                scan_id=scan_id,
                source_name=source_name,
                status=ScanSourceStatus(source_status),
                raw_result=subtask.get("raw_result"),
                error_message=subtask.get("error_message"),
            )
        )

        for asset in subtask.get("assets", []):
            stmt = pg_insert(Asset).values(
                scan_id=scan_id,
                identifier=asset["identifier"],
                asset_type=asset["asset_type"],
            ).on_conflict_do_nothing(
                index_elements=["scan_id", "identifier", "asset_type"]
            )
            await db.execute(stmt)

        for finding in subtask.get("findings", []):
            severity = Severity(finding.get("severity", "info").lower())
            db.add(
                Finding(
                    scan_id=scan_id,
                    source=finding.get("source", source_name),
                    severity=severity,
                    title=finding.get("title", "Unknown Finding"),
                    description=finding.get("description"),
                    recommendation=finding.get("recommendation"),
                    evidence=finding.get("evidence"),
                )
            )


@router.patch("/scans/{scan_id}/status", status_code=status.HTTP_200_OK)
async def update_scan_status_callback(
    scan_id: UUID,
    payload: ScanCallbackRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    queued_report = None

    try:
        scan = await ScanRepository.get_scan_by_id(db, scan_id)

        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

        scan.status = payload.status

        if payload.status == ScanStatus.COMPLETED:
            scan.progress = 100

        if payload.error_message:
            scan.error_message = payload.error_message

        if payload.results:
            await save_scan_callback_results(db, scan_id, payload.results)
            await db.commit()
            queued_report = await queue_report_generation(db, str(scan_id))
        else:
            await db.commit()

        logger.info("Scan %s updated to %s", scan_id, payload.status.value)

        return {
            "scan_id": str(scan_id),
            "status": payload.status.value,
            "report_status": queued_report["status"] if queued_report else None,
        }

    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        logger.exception("Failed to process worker callback for %s", scan_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process callback",
        ) from None

@router.patch("/reports/{scan_id}/status", status_code=status.HTTP_200_OK)
async def update_report_status_callback(
    scan_id: UUID,
    payload: ReportCallbackRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    try:
        if payload.status == "completed":
            if not payload.pdf_path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="pdf_path is required for completed reports",
                )

            report = await mark_report_completed(
                db=db,
                scan_id=str(scan_id),
                pdf_path=payload.pdf_path,
            )

        elif payload.status == "failed":
            report = await mark_report_failed(
                db=db,
                scan_id=str(scan_id),
                error_message=payload.error_message or "Report generation failed",
            )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid report status",
            )

        return {
            "scan_id": str(scan_id),
            "report_status": report.status.value,
        }

    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        logger.exception("Failed to process report callback for %s", scan_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process report callback",
        )