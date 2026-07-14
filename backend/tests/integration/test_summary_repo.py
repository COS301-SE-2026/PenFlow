import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.base import Severity
from app.models.finding import Finding
from app.models.report import Report
from app.models.report_status import ReportStatus
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
    assert previews[0]["severity"] == Severity.CRITICAL
    assert len(previews[0]["description"]) == 123
    assert previews[0]["description"].endswith("...")
    assert previews[1]["severity"] == Severity.LOW
    assert previews[1]["asset_identifier"] == "api.preview-test.com"

@pytest.mark.asyncio
async def test_get_asset_impact_summary(db_session: AsyncSession):
    scan = await scan_repo.ScanRepository.create_scan(db_session, "impact-test.com")

    ip_asset = Asset(scan_id=scan.id, identifier="192.168.1.1", asset_type="IP Address")
    safe_ip = Asset(scan_id=scan.id, identifier="10.0.0.1", asset_type="IP Address")
    sub_asset = Asset(scan_id=scan.id, identifier="dev.impact-test.com", asset_type="Subdomain")

    db_session.add_all([ip_asset, safe_ip, sub_asset])
    await db_session.commit()
    await db_session.refresh(ip_asset)
    await db_session.refresh(sub_asset)

    findings = [
        Finding(
            scan_id=scan.id, 
            asset_id=ip_asset.id,
            source="shodan", 
            severity=Severity.HIGH, 
            title="Vuln 1"
            ),
        Finding(
            scan_id=scan.id, 
            asset_id=sub_asset.id,
            source="crt.sh", 
            severity=Severity.INFO, 
            title="Info 1"
            ),
    ]
    db_session.add_all(findings)
    await db_session.commit()

    impact = await summary_repo.get_asset_impact_summary(db_session, scan.id)

    assert impact["total_assets_scanned"] ==3
    assert impact["affected_assets_count"] == 2

    breakdown = impact["asset_type_breakdown"]
    ip_breakdown = next(b for b in breakdown if b["asset_type"] == "IP Address")
    assert ip_breakdown["total_assets"] == 2
    assert ip_breakdown["affected_assets"] == 1

@pytest.mark.asyncio
async def test_get_source_coverage(db_session: AsyncSession):
    scan = await scan_repo.ScanRepository.create_scan(db_session, "coverage-test.com")

    sources = [
        ScanSource(scan_id=scan.id, source_name="shodan", status=ScanSourceStatus.COMPLETED),
        ScanSource(scan_id=scan.id, source_name="hibp", status=ScanSourceStatus.FAILED),
    ]
    db_session.add_all(sources)
    await db_session.commit()

    coverage = await summary_repo.get_source_coverage(db_session, scan.id)

    aggregate = coverage["aggregate"]
    assert aggregate["sources_total"] == 2
    assert aggregate["sources_completed"] == 1
    assert aggregate["sources_failed"] == 1
    assert aggregate["sources_partial"] == 0
    assert len(coverage["sources"]) == 2

@pytest.mark.asyncio
async def test_get_report_status(db_session: AsyncSession):
    scan = await scan_repo.ScanRepository.create_scan(db_session, "report-test.com")

    report = Report(scan_id=scan.id, status=ReportStatus.GENERATING)
    db_session.add(report)
    await db_session.commit()

    fetched_report = await summary_repo.get_report_status(db_session, scan.id)

    assert fetched_report is not None
    assert fetched_report.status == ReportStatus.GENERATING