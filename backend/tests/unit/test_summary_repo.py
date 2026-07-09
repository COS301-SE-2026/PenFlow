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

@pytest.mark.asyncio
async def test_get_risk_snapshot(db_session: AsyncSession):
    scan = await scan_repo.ScanRepository.create_scan(db_session, "risk-test.com")

    #seed 4 findings, 2 High, 1 Medium, 1 Info
    findings = [
        Finding(scan_id=scan.id, source="hibp", severity=Severity.HIGH, title="Breach 1"),
        Finding(scan_id=scan.id, source="urlscan", severity=Severity.HIGH, title="Malicious"),
        Finding(scan_id=scan.id, source="shodan", severity=Severity.MEDIUM, title="Open Port"),
        Finding(scan_id=scan.id, source="crt.sh", severity=Severity.INFO, title="Subdomain"),
    ]
    db_session.add_all(findings)
    await db_session.commit()

    snapshot = await summary_repo.get_risk_snapshot(db_session, scan.id)

    assert snapshot["total_findings"] == 4
    assert snapshot["high_count"] == 2
    assert snapshot["medium_count"] == 1
    assert snapshot["critical_count"] == 0
    assert snapshot["info_count"] == 1

@pytest.mark.asyncio
async def test_get_top_findings_preview(db_session: AsyncSession):
    scan = await scan_repo.ScanRepository.create_scan(db_session, "preview-test.com")
    asset = Asset(scan_id=scan.id, identifier="api.preview-test.com", asset_type="Subdomain")
    db_session.add(asset)
    await db_session.commit()
    await db_session.refresh(asset)

    #seed 1 critical, 1 low.
    long_desc = "A" * 150
    findings = [
        Finding(
            scan_id=scan.id,
            asset_id=asset.id,
            source="test",
            severity=Severity.LOW,
            title="Low Risk"
        ),
        Finding(
            scan_id=scan.id,
            source="test",
            severity=Severity.CRITICAL,
            title="Ctit Risk",
            description=long_desc
        ),
    ]
    db_session.add_all(findings)
    await db_session.commit()

    previews = await summary_repo.get_top_findings_preview(db_session, scan.id, limit=5)

    assert len(previews) == 2
    #crit first
    assert preview[0]["severity"] == Severity.CRITICAL
    assert len(previews[0]["description"]) == 123
    assert previews[0]["description"].endswith("...")
    assert previews[1]["severity"] == Severity.LOW
    assert previews[1]["asset_identifier"] == "api.preview-test.com"