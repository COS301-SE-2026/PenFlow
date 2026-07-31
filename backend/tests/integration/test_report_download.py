from uuid import uuid4

import pytest
from fastapi import status

from app.models.base import ScanStatus
from app.models.report import Report
from app.models.report_status import ReportStatus
from app.models.scan import Scan


@pytest.mark.asyncio
#phase2 download pdf happy path
async def test_download_completed_report_pdf(test_client, db_session, tmp_path):
    scan_id = uuid4()

    scan = Scan(
        id=scan_id,
        domain="example.com",
        status=ScanStatus.COMPLETED,
        progress=100,
    )
    db_session.add(scan)

    pdf_path = tmp_path / f"ctem_report_{scan_id}.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%Test PenFlow PDF\n")

    report = Report(
        scan_id=scan_id,
        status=ReportStatus.COMPLETED,
        pdf_path=str(pdf_path),
    )
    db_session.add(report)

    await db_session.commit()

    response = await test_client.get(f"/api/v1/scans/{scan_id}/pdf")

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_download_report_not_ready(test_client, db_session):
    scan_id = uuid4()

    scan = Scan(
        id=scan_id,
        domain="example.com",
        status=ScanStatus.COMPLETED,
        progress=100,
    )
    db_session.add(scan)

    report = Report(
        scan_id=scan_id,
        status=ReportStatus.GENERATING,
        pdf_path=None,
    )
    db_session.add(report)

    await db_session.commit()

    response = await test_client.get(f"/api/v1/scans/{scan_id}/pdf")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Report is not ready yet"