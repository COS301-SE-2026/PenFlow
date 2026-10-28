import os
import ssl
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


def internal_http_options(url: str) -> dict[str, Any]:
    parts = urlsplit(url)

    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.query
        or parts.fragment
    ):
        raise RuntimeError("Invalid internal backend URL")

    required = (
        os.getenv("APP_ENV", "").lower() == "production"
        or os.getenv("ENVIRONMENT", "").lower() == "production"
        or os.getenv(
            "INTERNAL_TLS_REQUIRED", "false"
        ).lower() == "true"
    )

    if required and parts.scheme != "https":
        raise RuntimeError(
            "Production internal requests require HTTPS"
        )

    verify: ssl.SSLContext | bool = True

    if parts.scheme == "https":
        root = Path(os.getenv(
            "INTERNAL_CA_FILE",
            "/app/certs/penflow-internal-ca.pem",
        ))

        if not root.is_file():
            raise RuntimeError(
                "Internal TLS CA bundle is missing"
            )

        context = ssl.create_default_context(
            cafile=str(root),
        )
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        verify = context

    return {
        "verify": verify,
        "trust_env": False,
        "follow_redirects": False,
    }