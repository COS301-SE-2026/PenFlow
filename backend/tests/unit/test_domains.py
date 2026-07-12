import pytest
from unittest.mock import patch
from uuid import UUID
from fastapi import status

from app.models.verified_domain import DomainVerificationStatus

@pytest.mark.asyncio
async def test_add_domain_for_verification(test_client):
    payload = {"domain": "pen-flow.com"}

    response = await test_client.post("/api/v1/domains/", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    assert data["domain"] == "pen-flow.com"
    assert data["status"] == "pending"
    assert data["verification_token"].startswith("penflow-verification=")
    assert "id" in data