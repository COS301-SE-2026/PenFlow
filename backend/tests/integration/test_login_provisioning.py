# Integration tests for user login and provisioning (UC-05).
# 
# These tests verify:
# 1. First login: Creates a new user row in the database
# 2. Subsequent logins: Updates existing user row (upsert)
# 3. Authentication required: Protected endpoints reject unauthenticated requests
#
# All tests use real database operations (no mocks) to verify the actual
# SQL and database constraints work correctly.

from sqlalchemy import text
from fastapi import status


async def test_first_login_creates_user_row(test_client, db_session, login_as):
    # Happy path: brand new Keycloak user gets a Postgres row on first login
    # Act: Login as a new user and get their profile
    # IMPORTANT: login_as is synchronous (just sets a dict override), so no await
    login_as({
        "sub": "kc-new-1",
        "email": "new-user@example.com",
        "name": "New User"
    })
    
    response = await test_client.get("/api/v1/users/me")

    # Assert: API response is correct
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["email"] == "new-user@example.com"
    assert body["role"] == "client"  # Default role for new users

    # Verify database row was created
    row = (await db_session.execute(
        text("SELECT email, auth_provider_id FROM users WHERE id = :id"),
        {"id": body["id"]},
    )).fetchone()
    
    assert row is not None
    assert row.email == "new-user@example.com"
    assert row.auth_provider_id == "kc-new-1"


async def test_second_login_updates_existing_row_not_duplicate(test_client, db_session, login_as):
    # Tests ON CONFLICT upsert: same user logs in again, row updates not duplicates
    # First login: Create the user
    #  login_as is synchronous (just sets a dict override), so no await
    login_as({"sub": "kc-existing-1", "email": "old@example.com"})
    first_response = await test_client.get("/api/v1/users/me")
    user_id = first_response.json()["id"]

    # Second login: Should update the existing user
    login_as({"sub": "kc-existing-1", "email": "changed@example.com"})
    second_response = await test_client.get("/api/v1/users/me")

    # Verify: Same ID, updated email
    assert second_response.json()["id"] == user_id  # Same user, not a duplicate
    assert second_response.json()["email"] == "changed@example.com"  # Email updated

    # Verify: Only one row exists for this auth_provider_id
    count = (await db_session.execute(
        text("SELECT COUNT(*) FROM users WHERE auth_provider_id = :sub"),
        {"sub": "kc-existing-1"},
    )).scalar_one()
    assert count == 1  # Ensures ON CONFLICT worked correctly


async def test_me_requires_authentication(test_client):
    # Error path: unauthenticated requests get 401 before touching database
    # Act: Attempt to access protected endpoint without authentication
    response = await test_client.get("/api/v1/users/me")
    
    # Assert: Rejected with 401 Unauthorized
    assert response.status_code == status.HTTP_401_UNAUTHORIZED