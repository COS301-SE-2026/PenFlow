from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from fastapi import status

# POST tests /scans/ (Initiate Scan)

@patch("app.services.scan_service.celery_app.send_task")
@patch("app.repositories.scan_repo.ScanRepository.create_scan", new_callable=AsyncMock)
def test_initiate_scan_success(mock_create_scan, mock_send_task, test_client):
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

    response = test_client.post("/api/v1/scans", json=payload)

    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()
    assert "scan_id" in data
    assert data["status"] == "queued"


def test_initiate_scan_invalid_domain(test_client):
    """Test missing required fields give a 422 Validation error"""
    payload = {
        #In this case I'll remove domain
        "email": "Jeandre@gmail.com"
    }
    response = test_client.post("/api/v1/scans/",json=payload)
    #Where pydantic comes in
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_download_scan_pdf(test_client):
    """Test that the pdf endpoint returns a file with correct headers"""
    mock_scan_id = "12345"
    response = test_client.get(f"/api/v1/scans/{mock_scan_id}/pdf")

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/pdf"
    assert f"filename=\"PenFlow_Report_{mock_scan_id}.pdf\"" in response.headers["content-disposition"] #noqa: E501


@patch("app.api.routes.internal.ScanRepository.get_scan_by_id", new_callable=AsyncMock)
def test_worker_failure_callback(mock_get_scan_by_id, test_client):
    mock_scan_id = "550e8400-e29b-41d4-a716-446655440000"

    mock_scan = MagicMock()
    mock_scan.id = UUID(mock_scan_id)
    mock_scan.status.value = "failed"
    mock_get_scan_by_id.return_value = mock_scan

    payload = {
        "status": "failed",
        "error_message": "Shodan API rate limit exceeded",
    }

    response = test_client.patch(
        f"/api/v1/internal/scans/{mock_scan_id}/status",
        json=payload,
    )

    assert response.status_code == status.HTTP_200_OK
