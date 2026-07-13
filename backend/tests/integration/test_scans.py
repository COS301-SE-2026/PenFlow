from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi import status


# POST tests /scans/ (Initiate Scan)
@pytest.mark.asyncio
@patch("app.services.scan_service.celery_app.send_task")
@patch("app.repositories.scan_repo.ScanRepository.create_scan", new_callable=AsyncMock)
async def test_initiate_scan_success(mock_create_scan, mock_send_task, test_client):
    mock_scan = MagicMock()
    mock_scan.id = UUID("550e8400-e29b-41d4-a716-446655440000")
    mock_scan.status = "queued"
    mock_create_scan.return_value = mock_scan

    mock_task = MagicMock()
    mock_task.id = "mock-task-id"
    mock_send_task.return_value = mock_task

    payload = {
        "domain": "jeandre.co",
        "email": "jeandre@gmail.com",
    }

    response = await test_client.post("/api/v1/scans/", json=payload)

    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()
    assert "scan_id" in data
    assert data["status"] == "queued"

@pytest.mark.asyncio
async def test_initiate_scan_invalid_domain(test_client):
    """Test missing required fields give a 422 Validation error"""
    payload = {
        #In this case I'll remove domain
        "email": "Jeandre@gmail.com"
    }
    response = await test_client.post("/api/v1/scans/",json=payload)
    #Where pydantic comes in
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

@pytest.mark.asyncio
@patch("app.api.routes.scans.get_report_by_scan_id")
async def test_download_scan_pdf(mock_get_report, test_client, tmp_path):
    """Test that the pdf endpoint returns a file with correct headers"""
    test_pdf = tmp_path / "test.pdf"
    test_pdf.write_bytes(b"%PDF-1.4\n%test pdf\n")
    mock_report = MagicMock()
    mock_report.status.value = "completed"
    mock_report.pdf_path = str(test_pdf)

    mock_get_report.return_value = mock_report

    response = await test_client.get(
        "/api/v1/scans/550e8400-e29b-41d4-a716-446655440000/pdf"
    )

    assert response.status_code == status.HTTP_200_OK

@pytest.mark.asyncio
@patch("app.api.routes.internal.ScanRepository.get_scan_by_id", new_callable=AsyncMock)
async def test_worker_failure_callback(mock_get_scan_by_id, test_client):
    mock_scan_id = "550e8400-e29b-41d4-a716-446655440000"

    mock_scan = MagicMock()
    mock_scan.id = UUID(mock_scan_id)
    mock_scan.status.value = "failed"
    mock_get_scan_by_id.return_value = mock_scan

    payload = {
        "status": "failed",
        "error_message": "Shodan API rate limit exceeded",
    }

    response = await test_client.patch(
        f"/api/v1/internal/scans/{mock_scan_id}/status",
        json=payload,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "failed"

@pytest.mark.asyncio
@patch("app.api.routes.scans.ScanRepository.list_scans", new_callable=AsyncMock)
async def test_list_scans_success(mock_list_scans, test_client):
    mock_list_scans.return_value = [
        {
        "id": UUID("550e8400-e29b-41d4-a716-446655440000"),
        "domain": "test.com",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "total_findings": 5,
        "critical_count": 0,
        "high_count": 1,
        "medium_count": 2,
        "low_count": 2,
        }
    ]

    response = await test_client.get("/api/v1/scans/")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["domain"] == "test.com"

@pytest.mark.asyncio
@patch("app.api.routes.scans.ScanRepository.get_scan_status", new_callable=AsyncMock)
async def test_get_scan_status_success(mock_get_status, test_client):
    mock_get_status.return_value = {
        "scan_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "running",
        "progress": 60,
        "sources": [],
        "report_status": None
    }

    response = await test_client.get("/api/v1/scans/550e8400-e29b-41d4-a716-446655440000/status")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["progress"] == 60

@pytest.mark.asyncio
@patch("app.api.routes.scans.ScanRepository.get_scan_status", new_callable=AsyncMock)
async def test_get_scan_status_not_found(mock_get_status, test_client):
    mock_get_status.return_value = None

    response = await test_client.get("/api/v1/scans/550e8400-e29b-41d4-a716-446655440000/status")

    assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
@patch("app.api.routes.scans.send_report_email")
@patch("app.api.routes.scans.get_report_by_scan_id", new_callable=AsyncMock)
@patch("app.api.routes.scans.ScanRepository.get_scan_by_id", new_callable=AsyncMock)
async def test_email_scan_report_success(
    mock_get_scan, 
    mock_get_report, 
    mock_send_email, 
    test_client
    ):
    # mocking the scan
    mock_scan =  MagicMock()
    mock_scan.domain = "jeandre.co"
    mock_get_scan.return_value = mock_scan

    # mock the compiled report
    mock_report = MagicMock()
    mock_report.status.value = "completed"
    mock_report.pdf_path = "/tmp/report.pdf"
    mock_get_report.return_value = mock_report

    payload = {"email": "client@example.co"}

    response = await test_client.post(
        "/api/v1/scans/550e8400-e29b-41d4-a716-446655440000/email-report",
        json=payload
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Report emailed successfully"
    mock_send_email.assert_called_once_with(
        to_email="client@example.co",
        domain="jeandre.co",
        pdf_path="/tmp/report.pdf"
    )

@pytest.mark.asyncio
@patch("app.api.routes.scans.get_report_by_scan_id")
async def test_download_scan_pdf_report_missing(mock_get_report, test_client):
    mock_get_report.return_value = None

    response = await test_client.get(
        "/api/v1/scans/550e8400-e29b-41d4-a716-446655440000/pdf",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
@patch("app.api.routes.scans.get_report_by_scan_id")
async def test_download_scan_pdf_uncompleted(mock_get_report, test_client):
    mock_report = MagicMock()
    mock_report.status.value = "generating"
    mock_get_report.return_value = mock_report
    response = await test_client.get(
        "/api/v1/scans/550e8400-e29b-41d4-a716-446655440000/pdf"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST