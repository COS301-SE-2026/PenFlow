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
    assert data["status"] == "pending"