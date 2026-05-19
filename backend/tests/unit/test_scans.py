from fastapi import status

# POST tests /scans/ (Initiate Scan)

def test_initiate_scan_success(test_client):
    """Test that a valid domain returns 202 Accepted and a scan_id"""
    payload = {
        "domain": "jeandre.co",
        "email": "jeandre@gmail.com"
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

def test_get_scan_report(test_client):
    """Test that returning a report returns the correct (mock) data structure"""
    mock_scan_id = "550e8400-e29b-41d4-a716-446655440000"
    response = test_client.get(f"/api/v1/scans/{mock_scan_id}/report")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    #verify structure
    assert data["scan_id"] == mock_scan_id
    assert "assets" in data
    assert len(data["assets"]) > 0
    assert "findings" in data["assets"][0]

def test_download_scan_pdf(test_client):
    """Test that the pdf endpoint returns a file with correct headers"""
    mock_scan_id = "12345"
    response = test_client.get(f"/api/v1/scans/{mock_scan_id}/pdf")

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/pdf"
    assert f"filename=\"PenFlow_Report_{mock_scan_id}.pdf\"" in response.headers["content-disposition"]

def test_worker_failure_callback(test_client):
    """Tests that a worker can report a failure successfully"""
    mock_scan_id = "550e8400-e29b-41d4-a716-446655440000"
    payload = {
        "status": "failed",
        "error_message": "Shodan API rate limit exceeded"
    }

    response = test_client.patch(f"/api/v1/internal/scans/{mock_scan_id}/status", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == f"Scan {mock_scan_id} updated to failed"
