#phase 2 findings integration test



from uuid import uuid4

import pytest
from fastapi import status

from app.models.asset import Asset
from app.models.base import ScanStatus, Severity
from app.models.finding import Finding
from app.models.scan import Scan


#phase2
#GET /scans/{scan_id}/findings happy path intergration
#integrate http layer,finding  repo , database working together
@pytest.mark.asyncio
async def test_get_scan_findings_success(test_client, db_session):
    scan_id = uuid4()
    scan = Scan(id=scan_id, domain="findings-test.com", status=ScanStatus.COMPLETED, progress=100)
    db_session.add(scan)
    await db_session.flush()

    asset = Asset(scan_id=scan_id, identifier="findings-test.com", asset_type="domain")
    db_session.add(asset)
    await db_session.flush()

    finding = Finding(
        scan_id=scan_id,
        asset_id=asset.id,
        source="nmap",
        severity=Severity.HIGH,
        title="Outdated TLS version",
        description="Server supports TLS 1.0",
        recommendation="Disable TLS 1.0 and 1.1",
        evidence={},
    )
    db_session.add(finding)
    await db_session.commit()

    response = await test_client.get(f"/api/v1/scans/{scan_id}/findings")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Outdated TLS version"
    assert data[0]["severity"] == "high"
    assert data[0]["asset_identifier"] == "findings-test.com"


#phase2
#GET /scans/{scan_id}/findings error/edge path intergration - no findings for scan
@pytest.mark.asyncio
async def test_get_scan_findings_empty(test_client, db_session):
    scan_id = uuid4()
    scan = Scan(id=scan_id, domain="no-findings.com", status=ScanStatus.COMPLETED, progress=100)
    db_session.add(scan)
    await db_session.commit()

    response = await test_client.get(f"/api/v1/scans/{scan_id}/findings")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []
