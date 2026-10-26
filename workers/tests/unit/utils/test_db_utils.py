from app.utils.db_utils import _get_db_url


def test_database_url(monkeypatch):
    (monkeypatch.setenv
    (
        "DATABASE_URL",
        "postgresql+asyncpg://user:pass@localhost/test",
    ))
    monkeypatch.delenv("DATABASE_HOST", raising=False)
    monkeypatch.delenv("DATABASE_NAME", raising=False)
    monkeypatch.delenv("DATABASE_USER", raising=False)
    monkeypatch.delenv("DATABASE_PASSWORD", raising=False)
    result = _get_db_url()
    assert result == "postgresql://user:pass@localhost/test"


def test_database_env(monkeypatch):
    monkeypatch.setenv("DATABASE_HOST", "localhost")
    monkeypatch.setenv("DATABASE_PORT", "5432")
    monkeypatch.setenv("DATABASE_NAME", "penflow")
    monkeypatch.setenv("DATABASE_USER", "user")
    monkeypatch.setenv("DATABASE_PASSWORD", "pass")

    result = _get_db_url()
    assert "localhost" in result
    assert "penflow" in result


def test_database_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_HOST", raising=False)
    monkeypatch.delenv("DATABASE_NAME", raising=False)
    monkeypatch.delenv("DATABASE_USER", raising=False)
    monkeypatch.delenv("DATABASE_PASSWORD", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    try:
        _get_db_url()
        assert False
    except RuntimeError:
        assert True