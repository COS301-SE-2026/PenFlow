from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.user_repo import get_or_create_user


def _make_row(id_="550e8400-e29b-41d4-a716-446655440000", email="test@example.com", role="client"):
    row = MagicMock()
    row.id = id_
    row.email = email
    row.role = role
    return row


def _make_db(row):
    # db.execute is async and must be awaited, but its return value
    db = MagicMock()
    result = MagicMock()
    result.fetchone.return_value = row
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_get_or_create_user_returns_expected_dict():
    db = _make_db(_make_row())

    result = await get_or_create_user(
        db=db,
        auth_provider_id="kc-123",
        email="test@example.com",
        full_name="Test User",
    )

    assert result == {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "email": "test@example.com",
        "role": "client",
    }


@pytest.mark.asyncio
async def test_get_or_create_user_commits_transaction():
    db = _make_db(_make_row())

    await get_or_create_user(
        db=db,
        auth_provider_id="kc-123",
        email="test@example.com",
    )

    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_or_create_user_passes_correct_query_params():
    db = _make_db(_make_row())

    await get_or_create_user(
        db=db,
        auth_provider_id="kc-456",
        email="jane@example.com",
        full_name="Jane Doe",
    )

    _, params = db.execute.call_args.args
    assert params == {
        "auth_provider_id": "kc-456",
        "email": "jane@example.com",
        "full_name": "Jane Doe",
    }


@pytest.mark.asyncio
async def test_get_or_create_user_defaults_full_name_to_none():
    db = _make_db(_make_row())

    await get_or_create_user(
        db=db,
        auth_provider_id="kc-789",
        email="no-name@example.com",
    )

    _, params = db.execute.call_args.args
    assert params["full_name"] is None

# unit test error handling if no database qury return nothing for creating a user
@pytest.mark.asyncio
async def test_get_or_create_user_raises_when_no_row_returned():
    db = _make_db(row= None)

    with pytest.raises(RuntimeError,match = "kc-missing"):
        await get_or_create_user(
            db=db,
            auth_provider_id = "kc-missing",
            email = "ghost@example.com"
        )