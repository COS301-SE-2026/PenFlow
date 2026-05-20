from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import summary_repo
from app.schemas.summary import ScanSummary
from app.utils.db import get_db

router = APIRouter(prefix="/scans", tags=["Executive Summary"])

@router.get("/{scan_id}/summary", response_model=ScanSummary, status_code=status.HTTP_200_OK)
async def get_scan_summary(
    scan_id: UUID,
    db: AsyncSession = Depends(get_db)
)-> Any:
    """
    Generates  complete Executive summary for a specific scan.
    """
    scan_data = await summary_repo.get_scan_summary(db, scan_id)

    if not scan_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID {scan_id} not found."

        )
    return scan_data
