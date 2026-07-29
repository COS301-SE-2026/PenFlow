import logging
import os
import socket
import ssl
import tempfile
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]

# Services we expect from the nmap port scan
TLS_SERVICES = [
    "https",
    "https-alt",
    "ssl",
    "tls",
]


# tls ports
TLS_PORTS = [
    443,
    8443,
    9443,
    10443,
]


def run_tls_scan(
    ip_address: str,
    ports: list[JSONDict],
    hostname: str | None = None,
    timeout: int = 5,
) -> JSONDict:
    """
    Does tls inspection off of the valid ports provided by nmap
    """

    logger.info(f"[TLS_Service] Starting TLS scan against IP address: {ip_address}")

    result: JSONDict = {
        "ip": ip_address,
        "targets": [],
    }

    for port in ports:
        service = (port.get("service") or "").lower()

        # skip non tls stuff
        if (
            port["port"] not in TLS_PORTS
            and "https" not in service
            and "ssl" not in service
            and "tls" not in service
        ):
            continue

        try:
            # need to create context to verify records
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            # tcp conn
            with socket.create_connection(
                (
                    ip_address,
                    port["port"],
                ),
                timeout=timeout,
            ) as socket_connection:
                # tls handshake
                with context.wrap_socket(
                    socket_connection,
                    server_hostname=hostname or ip_address,
                ) as tls_socket:
                    # receive binary certificate
                    binary_certificate = tls_socket.getpeercert(binary_form=True)

                    if binary_certificate is None:
                        raise ssl.SSLError("Server did not provide a certificate.")

                    # make binary readable format
                    readable_cert = ssl.DER_cert_to_PEM_cert(binary_certificate)

                    # python needs a filename for the standard library
                    # decoder so we save the readable cert in a file
                    # and provide the file
                    with tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=".pem",
                    ) as temp_cert_file:
                        temp_cert_file.write(readable_cert.encode())

                        temporary_cert_path = temp_cert_file.name

                    try:
                        decoded_cert = ssl._ssl._test_decode_cert(temporary_cert_path)

                    finally:
                        os.unlink(temporary_cert_path)

                    # extract what we want
                    # subject
                    # issuer
                    # valid from
                    # valid until
                    subject = dict(
                        item[0]
                        for item in decoded_cert.get(
                            "subject",
                            [],
                        )
                    )

                    issuer = dict(
                        item[0]
                        for item in decoded_cert.get(
                            "issuer",
                            [],
                        )
                    )

                    valid_from = decoded_cert.get("notBefore")

                    valid_until = decoded_cert.get("notAfter")

                    # Calc if expired
                    # calc has to take timezones into account
                    expired = False

                    if valid_until:
                        expiry = datetime.strptime(
                            valid_until,
                            "%b %d %H:%M:%S %Y %Z",
                        ).replace(tzinfo=UTC)

                        expired = expiry < datetime.now(UTC)

                    parsed_target = {
                        "port": port["port"],
                        "tls_version": tls_socket.version(),
                        "cipher": tls_socket.cipher(),
                        "certificate": {
                            "subject": subject,
                            "issuer": issuer,
                            "valid_from": valid_from,
                            "valid_until": valid_until,
                            "expired": expired,
                            # self_signed if the issuer is equal to the subject
                            "self_signed": (bool(subject) and bool(issuer) and subject == issuer),
                        },
                    }

                    result["targets"].append(parsed_target)

        except (
            ssl.SSLError,
            socket.timeout,
            OSError,
        ) as error:
            logger.warning(
                f"[TLS_Service] Failed TLS handshake on {ip_address}:{port['port']} - {error}"
            )

            result["targets"].append(
                {
                    "port": port["port"],
                    "error": str(error),
                }
            )

    logger.info(
        f"[TLS_Service] Completed TLS scan against IP address: "
        f"{ip_address}. "
        f"Inspected {len(result['targets'])} TLS endpoint(s)."
    )

    return result
