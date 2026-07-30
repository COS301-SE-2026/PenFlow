from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi import status

from app.api.middleware.auth import get_current_user
from app.main import app
from app.models.user import User
from app.models.verified_domain import (
    DomainVerificationCode,
    DomainVerificationStatus,
    VerifiedDomain,
)


@pytest_asyncio.fixture
async def test_user(db_session):
    user = User(
        id = UUID("12345678-1234-5678-1234-567812345679"),
        auth_provider = "keycloak",
        auth_provider_id = "12345678-1234-5678-1234-567812345678",
        email = "myemail@gmail.com",
        full_name = "test user",
        role = "client",
    )

    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)

    return user


async def override_get_current_user():
    return {"sub": "12345678-1234-5678-1234-567812345678", "role": "client"}

app.dependency_overrides[get_current_user] = override_get_current_user

#Phase 2 
#test adding domain successs verified 
# POST /domains/ (add domain) happy path intergration 
@pytest.mark.asyncio
async def test_add_domain_for_verification(test_client, test_user):
    app.dependency_overrides[get_current_user] = override_get_current_user

    payload = {"domain": "pen-flow.com"}

    response = await test_client.post("/api/v1/domains/", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    assert data["domain"] == "pen-flow.com"
    assert data["status"] == "pending"
    assert data["verification_token"].startswith("penflow-verification=")
    assert "id" in data

@pytest.mark.asyncio
@patch("app.services.domain_service.VerificationService.verify_dns_txt", new_callable=AsyncMock)
async def test_verify_domain_ownership_success(mock_verify_txt, test_client, test_user):
    #force a true
    mock_verify_txt.return_value = DomainVerificationCode.VERIFIED

    app.dependency_overrides[get_current_user] = override_get_current_user

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

#phase2
#POST /domains/{domain_id}/verify error  path verify domain
@pytest.mark.asyncio
@patch("app.services.domain_service.VerificationService.verify_dns_txt", new_callable=AsyncMock)
async def test_verify_domain_ownership_fail(mock_verify_txt, test_client, test_user):
    #force a false
    mock_verify_txt.return_value = DomainVerificationCode.TOKEN_MISMATCH

    app.dependency_overrides[get_current_user] = override_get_current_user

    #add a domain
    add_response = await test_client.post(
        "/api/v1/domains/",
        json={"domain": "fail-test.com"}
    )
    domain_id = add_response.json()["id"]

    #hit the verification endpoint
    verify_response = await test_client.post(f"/api/v1/domains/{domain_id}/verify")

    assert verify_response.status_code == status.HTTP_400_BAD_REQUEST
    assert "A TXT record was found, "
    "but the verification token did not match." in verify_response.json()["detail"]

@pytest.mark.asyncio
async def test_verify_domain_not_found(test_client, test_user):
    #fake uuid
    app.dependency_overrides[get_current_user] = override_get_current_user
    fake_id = "00000000-0000-0000-0000-000000000000"

    verify_response = await test_client.post(f"/api/v1/domains/{fake_id}/verify")

    assert verify_response.status_code == status.HTTP_404_NOT_FOUND

#phase 2 add domain intergration test
#delete domain happy path 
async def test_domain_success(test_client, test_user, db_session):
    app.dependency_overrides[get_current_user] = override_get_current_user
    add_response = await test_client.post(
        "/api/v1/domains/",
        json={"domain": "delete-me.com"}
    )

    domain_id = add_response.json()["id"]


    delete_response = await test_client.delete(f"/api/v1/domains/{domain_id}")

    assert delete_response.status_code == status.HTTP_204_NO_CONTENT

    #verify the db
    result = await db_session.get(VerifiedDomain, UUID(domain_id))

    assert result is None

#delete domain error path domain not exist
async def test_delete_domain_not_found(test_client, test_user):
    app.dependency_overrides[get_current_user] = override_get_current_user
    fake_id = "00000000-0000-0000-0000-000000000000"

    delete_response = await test_client.delete(f"/api/v1/domains/{fake_id}")

    assert delete_response.status_code == status.HTTP_404_NOT_FOUND