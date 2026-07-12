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

@pytest.mark.asyncio
@patch("app.api.routes.domains.VerificationService.verify_dns_txt")
async def test_verify_domain_ownership_success(mock_verify_txt, test_client):
    #force a true
    mock_verify_txt.return_value = True

    #add domain to db
    add_response = await test_client.post(
        "/api/v1/domains/",
        json={"domain": "pass-test.com"}
    )
    domain_id = add_response.json()["id"]

    #use the verification endpoint
    verify_response = await test_client.post(f"/api/v1/domains/{domain_id}/verify")

    assert verify_response.status_code == status.HTTP_200_OK
    data = verify_response.json()

    assert data["status"] == DomainVerificationStatus.VERIFIED.value
    assert data["verified_at"] is not None

@pytest.mark.asyncio
@patch("app.api.routes.domains.VerificationService.verify_dns_txt")
async def test_verify_domain_ownership_fail(mock_verify_txt, test_client):
    #force a false
    mock_verify_txt.return_value = False

    #add a domain
    add_response = await test_client.post(
        "/api/v1/domains/",
        json={"domain": "fail-test.com"}
    )
    domain_id = add_response.json()["id"]

    #hit the verification endpoint
    verify_response = await test_client.post(f"/api/v1/domains/{domain_id}/verify")

    assert verify_response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Verification failed" in verify_response.json()["detail"]

@pytest.mark.asyncio
async def test_verify_domain_not_found(test_client):
    #fake uuid
    fake_id = "00000000-0000-0000-0000-000000000000"

    verify_response = await test_client.post(f"/api/v1/domains/{fake_id}/verify")

    assert verify_response.status_code == status.HTTP_404_NOT_FOUND