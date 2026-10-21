import os
import ssl
from pathlib import Path
from typing import Any

from sqlalchemy.engine import make_url


def get_database_connect_args(
        database_url: str,
) -> dict[str, Any]:
    production = (
        os.getenv("APP_ENV", "development").lower()
        == "production"
    )

    mode = os.getenv(
        "DATABASE_SSL_MODE",
        "verify-full" if production else "disable",
    ).lower()

    if mode not in {"disable", "verify-full"}:
        raise RuntimeError(
            "DATABASE_SSL_MODE must be disable or verify-full"
        )

    if production and mode != "verify-full":
        raise RuntimeError(
            "Production database connections require verify-full"
        )

    url = make_url(database_url)

    if url.drivername != "postgresql+asyncpg":
        raise RuntimeError(
            "The backend requires the asyncpg PostgreSQL driver"
        )

    if any(
        name.lower().startswith("ssl")
        or name.lower() in {"host", "hostaddr"}
        for name in url.query
    ):
        raise RuntimeError(
            "Configure database TLS with DATABASE_SSL_MODE "
            "and DATABASE_SSL_ROOT_CERT, not URL parameters"
        )

    if mode == "disable":
        return {"ssl": False}

    if not url.host or url.host.startswith("/"):
        raise RuntimeError(
            "Verified database TLS requires an explicit TCP hostname"
        )

    root = Path(os.getenv(
        "DATABASE_SSL_ROOT_CERT",
        "/app/certs/rds-global-bundle.pem",
    ))

    if not root.is_file():
        raise RuntimeError(
            "Database CA bundle is missing"
        )

    context = ssl.create_default_context(
        cafile=str(root),
    )

    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED

    return {"ssl": context}