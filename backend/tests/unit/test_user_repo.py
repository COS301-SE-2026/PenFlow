from unittest.mock import MagicMock

from app.repositories.user_repo import get_or_create_user


def _make_row(id_="550e8400-e29b-41d4-a716-446655440000", email="test@example.com", role="client"):
    row = MagicMock()
    row.id = id_
    row.email = email
    row.role = role
    return row


def test_get_or_create_user_returns_expected_dict():
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = _make_row()

    result = get_or_create_user(
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


def test_get_or_create_user_commits_transaction():
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = _make_row()

    get_or_create_user(
        db=db,
        auth_provider_id="kc-123",
        email="test@example.com"
    )

    db.commit.assert_called_once()


def test_get_or_create_user_passes_correct_query_params():
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = _make_row()

    get_or_create_user(
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


def test_get_or_create_user_defaults_full_name_to_none():
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = _make_row()

    get_or_create_user(
        db=db,
        auth_provider_id="kc-789",
        email="no-name@example.com"
    )

    _, params = db.execute.call_args.args
    assert params["full_name"] is None