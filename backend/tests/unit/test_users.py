from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.routes.users import provision_user


@pytest.mark.asyncio
async def test_provision_user_returns_provisioned_user():
    current_user = {"sub": "kc-123", "email": "test@example.com", "name": "Test User"}
    db = MagicMock()
    expected = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "test@example.com",
        "role": "client",
    }

    with patch(
        "app.api.routes.users.get_or_create_user", new=AsyncMock(return_value=expected)
    ) as mock_get_or_create:
        result = await provision_user(current_user=current_user, db=db)

    assert result == expected
    mock_get_or_create.assert_called_once_with(
        db=db,
        auth_provider_id="kc-123",
        email="test@example.com",
        full_name="Test User",
    )


@pytest.mark.asyncio
async def test_provision_user_defaults_missing_email_to_empty_string():
    current_user = {"sub": "kc-456"}
    db = MagicMock()
    expected = {"id": "id-2", "email": "", "role": "client"}

    with patch(
        "app.api.routes.users.get_or_create_user", new=AsyncMock(return_value=expected)
    ) as mock_get_or_create:
        await provision_user(current_user=current_user, db=db)

    mock_get_or_create.assert_called_once_with(
        db=db,
        auth_provider_id="kc-456",
        email="",
        full_name=None,
    )


@pytest.mark.asyncio
async def test_provision_user_wraps_db_errors_as_500():
    current_user = {"sub": "kc-789", "email": "test@example.com"}
    db = MagicMock()

    with patch(
        "app.api.routes.users.get_or_create_user",
        new=AsyncMock(side_effect=RuntimeError("db down")),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await provision_user(current_user=current_user, db=db)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Failed to provision user"