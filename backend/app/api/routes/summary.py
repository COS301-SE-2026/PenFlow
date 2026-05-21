from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import summary_repo
from app.schemas.summary import ExecutiveSummary
from app.utils.db import get_db

router = APIRouter(prefix="/scans", tags=["Executive Summary"])

@router.get("/{scan_id}/summary", response_model=ExecutiveSummary, status_code=status.HTTP_200_OK)
async def get_scan_summary(
    scan_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Generates the complete Executive Summary for a specific scan.
    Currently compiled blocks:
    - Block 1: Scan Summary
    - Block 2: Risk Snapshot
    - Block 3: Top Findings Preview
    """
    scan_data = await summary_repo.get_scan_summary(db, scan_id)

    if not scan_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan with ID {scan_id} not found."

        )
    
    risk_data = await summary_repo.get_risk_snapshot(db, scan_id)

    top_findings_data = await summary_repo.get_top_findings_preview(db, scan_id, limit=5)

    asset_impact_data = await summary_repo.get_asset_impact_summary(db, scan_id)

    source_coverage_data = await summary_repo.get_source_coverage(db, scan_id)

    report_data = await summary_repo.get_report_status(db, scan_id)

    return {
        "scan_summary": scan_data,
        "risk_snapshot": risk_data,
        "top_findings": top_findings_data,
        "asset_impact": asset_impact_data,
        "source_coverage": source_coverage_data,
        "report_status": report_data
    }
