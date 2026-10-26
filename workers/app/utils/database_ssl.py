import os
from pathlib import Path

from psycopg2.extensions import parse_dsn


def get_database_connect_kwargs(
        dsn: str,
) -> dict[str, str]:
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

    if mode == "disable":
        return {
            "sslmode": "disable",
            "gssencmode": "disable",
        }

    host = parse_dsn(dsn).get("host", "")

    if not host or host.startswith("/"):
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

    return {
        "sslmode": "verify-full",
        "sslrootcert": str(root),
        "ssl_min_protocol_version": "TLSv1.2",
        "gssencmode": "disable",
    }