#Integration tests for user login and provisioning (UC-05).
#1 First login: Creates a new user row in the database
#2. Subsequent logins: Updates existing user row (upsert)
#3. Authentication required: Protected endpoints reject unauthenticated requests

#All tests use real database operations (no mocks) to verify the actual
#SQL and database constraints work correctly.

from sqlalchemy import text
from fastapi import status

async def test_first_login_creates_user_row(test_client, db_session, login_as):

  # Act: Login as a new user and get their profile
    await login_as({
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

    # Assert: Database row was created correctly
    # Query the actual database to verify the row exists
    row = (await db_session.execute(
        text("SELECT email, auth_provider_id FROM users WHERE id = :id"),
        {"id": body["id"]},
    )).fetchone()
    
    assert row is not None
    assert row.email == "new-user@example.com"
    assert row.auth_provider_id == "kc-new-1"