from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check(test_client):
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "api_version" in data
    assert "database" in data