import os
import shutil
import ssl
import tempfile
from pathlib import Path


def server_command() -> tuple[list[str], dict[str, str]]:
    environment = dict(os.environ)
    certificate = environment.pop("BACKEND_TLS_CERTIFICATE", "")
    private_key = environment.pop("BACKEND_TLS_PRIVATE_KEY", "")

    enabled = environment.get(
        "BACKEND_TLS_ENABLED", "false"
    ).lower()

    production = (
        environment.get("APP_ENV", "development").lower()
        == "production"
    )

    if enabled not in {"true", "false"}:
        raise RuntimeError(
            "BACKEND_TLS_ENABLED must be true or false"
        )

    if production and enabled != "true":
        raise RuntimeError("Production backend requires TLS")

    command = [
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "3001",
        "--no-proxy-headers",
    ]

    if enabled == "false":
        return command, environment

    if not certificate or not private_key:
        raise RuntimeError(
            "Backend TLS certificate and private key are required"
        )

    directory = Path(
        tempfile.mkdtemp(prefix="penflow-backend-tls-")
    )

    try:
        for name, value in (
            ("certificate.pem", certificate),
            ("private-key.pem", private_key),
        ):
            path = directory / name
            descriptor = os.open(
                path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )

            with os.fdopen(descriptor, "w") as handle:
                handle.write(value)

        certificate_path = directory / "certificate.pem"
        key_path = directory / "private-key.pem"

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(
            str(certificate_path),
            str(key_path),
        )

    except (OSError, ValueError):
        shutil.rmtree(directory)
        raise RuntimeError(
            "Backend TLS certificate/key are invalid"
        ) from None

    command.extend([
        "--ssl-certfile",
        str(certificate_path),
        "--ssl-keyfile",
        str(key_path),
        "--ssl-version",
        str(int(ssl.PROTOCOL_TLS_SERVER)),
    ])

    return command, environment


def main() -> None:
    command, environment = server_command()
    os.execvpe(command[0], command, environment)


if __name__ == "__main__":
    main()