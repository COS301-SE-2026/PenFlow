import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.internal_auth import require_internal_worker
from app.models.asset import Asset
from app.models.base import ReportStatus, ScanSourceStatus, ScanStatus, Severity
from app.models.finding import Finding
from app.models.scan_source import ScanSource
from app.queue.celery_app import celery_app
from app.repositories.report_repository import (
    get_by_engagement_and_version,
    get_report_by_scan_id,
)
from app.repositories.scan_repo import (
    SCAN_SOURCES_BY_TYPE,
    ScanRepository,
)
from app.schemas.report import ReportCallbackRequest
from app.schemas.scan import ScanCallbackRequest, ScanSourceCallbackRequest
from app.services.callback_validation import apply_report_callback
from app.services.phase2_execution_service import (
    ExecutionRequest,
    Phase2ExecutionService,
)
from app.services.report_service import queue_report_generation
from app.utils.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/internal",
    tags=["Internal Webhooks"],
    dependencies=[Depends(require_internal_worker)],
)


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
            stmt = (
                pg_insert(Asset)
                .values(
                    scan_id=scan_id,
                    identifier=asset["identifier"],
                    asset_type=asset["asset_type"],
                )
                .on_conflict_do_nothing(index_elements=["scan_id", "identifier", "asset_type"])
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

        await db.commit()

        if payload.status in [ScanStatus.COMPLETED, ScanStatus.PARTIAL]:
            queued_report = await queue_report_generation(db, str(scan_id))

            celery_app.send_task(
                "rag.index_scan",
                args=[str(scan_id)],
                queue="indexing",
                routing_key="indexing",
            )

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


@router.patch(
    "/reports/{scan_id}/status",
    status_code=status.HTTP_200_OK,
)
async def update_report_status_callback(
    scan_id: UUID,
    payload: ReportCallbackRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    report = await get_report_by_scan_id(
        db,
        str(scan_id),
    )

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    changed = apply_report_callback(report, payload)

    if changed:
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    return {
        "scan_id": str(scan_id),
        "report_status": report.status.value,
    }


@router.patch("/scans/{scan_id}/sources/{source_name}", status_code=status.HTTP_200_OK)
async def update_scan_source_callback(
    scan_id: UUID,
    source_name: str,
    payload: ScanSourceCallbackRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    scan = await ScanRepository.get_scan_by_id(db, scan_id)

    if scan is None:
        raise HTTPException(404, "Scan not found")

    expected_sources = SCAN_SOURCES_BY_TYPE.get(
        scan.scan_type.value,
        (),
    )

    if source_name not in expected_sources:
        raise HTTPException(
            status_code=422,
            detail="Source is not permitted for this scan type",
        )

    if payload.status not in {
        item.value for item in ScanSourceStatus
    }:
        raise HTTPException(
            status_code=422,
            detail="Invalid source status",
        )
    
    try:
        scan = await ScanRepository.save_source_result(
            db=db,
            scan_id=scan_id,
            source_name=source_name,
            payload=payload.model_dump(),
        )

        report_queued = None
        if scan.status in [ScanStatus.COMPLETED, ScanStatus.PARTIAL]:
            report = await get_report_by_scan_id(db, str(scan_id))
            if report is None or report.status not in [
                ReportStatus.GENERATING,
                ReportStatus.COMPLETED,
            ]:
                report_queued = await queue_report_generation(db, str(scan_id))

            celery_app.send_task(
                "rag.index_scan",
                args=[str(scan_id)],
                queue="indexing",
                routing_key="indexing",
            )

        return {
            "scan_id": str(scan.id),
            "source_name": source_name,
            "scan_status": scan.status.value,
            "progress": scan.progress,
            "report_status": report_queued["status"] if report_queued else None,
        }

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )

    except Exception:
        logger.exception(
            "Failed to process the source callback for scan %s source %s",
            scan_id,
            source_name,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process source callback",
        )


@router.put(
    "/reports/engagement/{engagement_id}/version/{version}/callback",
    status_code=status.HTTP_200_OK,
)
async def update_engagement_report_status_callback(
    engagement_id: UUID,
    version: int,
    payload: ReportCallbackRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    report = await get_by_engagement_and_version(db, engagement_id, version)

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Engagement report not found",
        )

    changed = apply_report_callback(report, payload)

    if changed:
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    return {
        "engagement_id": str(engagement_id),
        "version": version,
        "report_status": report.status.value,
    }


@router.post("/scans/{scan_id}/authorise-execution")
async def authorise_phase2_execution(
    scan_id: UUID,
    payload: ExecutionRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await Phase2ExecutionService.authorise(
        db,
        scan_id,
        payload,
    )