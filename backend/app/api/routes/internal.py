import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.base import ScanStatus, Severity
from app.models.finding import Finding
from app.repositories.scan_repo import ScanRepository
from app.schemas.scan import ScanCallbackRequest
from app.utils.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["Internal Webhooks"])


@router.patch("/scans/{scan_id}/status", status_code=status.HTTP_200_OK)
async def update_scan_status_callback(
    scan_id: str,
    payload: ScanCallbackRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    safe_id = scan_id.replace("\n", "").replace("\r", "")

    try:
        scan = await ScanRepository.get_scan_by_id(db, UUID(safe_id))
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

        scan.status = payload.status
        if payload.status == ScanStatus.COMPLETED:
            scan.progress = 100
        if payload.error_message:
            scan.error_message = payload.error_message

        if payload.results:
            for subtask in payload.results.get("subtasks", []):
                for a in subtask.get("assets", []):
                    stmt = pg_insert(Asset).values(
                        scan_id=UUID(safe_id),
                        identifier=a["identifier"],
                        asset_type=a["asset_type"],
                    ).on_conflict_do_nothing(constraint="uq_scan_identifier_type")
                    await db.execute(stmt)

                for f in subtask.get("findings", []):
                    sev = Severity(f.get("severity", "info").lower())
                    db.add(Finding(
                        scan_id=UUID(safe_id),
                        source=f.get("source", subtask.get("source_name", "unknown")),
                        severity=sev,
                        title=f.get("title", "Unknown Finding"),
                        description=f.get("description"),
                        recommendation=f.get("recommendation"),
                    ))

        await db.commit()
        logger.info("Scan %s updated to %s", safe_id, payload.status.value)
        return {"message": f"Scan {safe_id} updated to {payload.status.value}"}

    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        logger.exception("Failed to process worker callback for %s", safe_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process callback",
        )
