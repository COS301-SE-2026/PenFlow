import pytest

from app.config.database import get_database_url


def test_get_database_url_aws_environment(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_HOST", "host")
    monkeypatch.setenv("DATABASE_PORT", "1234")
    monkeypatch.setenv("DATABASE_NAME", "penflow")
    monkeypatch.setenv("DATABASE_USER", "me")
    monkeypatch.setenv("DATABASE_PASSWORD", "secretpass")

    result = get_database_url()

    assert result == "postgresql+asyncpg://me:secretpass@host:1234/penflow"



def test_get_database_url_error_config_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    required_variables = {
        "DATABASE_HOST",
        "DATABASE_PORT",
        "DATABASE_NAME",
        "DATABASE_USER",
        "DATABASE_PASSWORD",
    }

    for var in required_variables:
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(
        RuntimeError, match=(
            "Database config is missing. Missing: DATABASE_HOST, DATABASE_PORT, DATABASE_NAME, "
            "DATABASE_USER, DATABASE_PASSWORD"
        ),
    ):
        get_database_url()