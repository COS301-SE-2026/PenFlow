import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.base import Severity
from app.models.finding import Finding
from app.models.report import Report
from app.models.report_status import ReportStatus
from app.models.scan import Scan
from app.models.scan_source import ScanSource, ScanSourceStatus
from app.repositories import scan_repo, summary_repo

@pytest.mark.asyncio
async def test_get_scan_summary(db_session: AsyncSession):
    new_scan = await scan_repo.ScanRepository.create_scan(db_session, "summary-test.com")
    summary = await summary_repo.get_scan_summary(db_session, new_scan.id)

    assert summary is not None
    assert summary.id == new_scan.id
    assert summary.domain == "summary-test.com"