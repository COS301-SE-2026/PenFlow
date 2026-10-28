import hashlib
import hmac
import ipaddress
import os
import time

from fastapi import HTTPException, Request

LOCAL_PROXY_SECRET = (
    "local-only-rate-limit-proxy-secret-change-for-production"
)


def proxy_secret() -> str:
    value = os.getenv("RATE_LIMIT_PROXY_SECRET", "")
    production = (
        os.getenv("APP_ENV", "development").lower()
        == "production"
    )

    if not value and not production:
        value = LOCAL_PROXY_SECRET

    if len(value.encode()) < 32:
        raise RuntimeError(
            "RATE_LIMIT_PROXY_SECRET must contain at least 32 bytes"
        )

    return value


def canonical_ip(value: str) -> str:
    if "%" in value:
        raise ValueError(
            "Scoped IP addresses are not supported"
        )

    address = ipaddress.ip_address(value)

    if (
        isinstance(address, ipaddress.IPv6Address)
        and address.ipv4_mapped
    ):
        return str(address.ipv4_mapped)

    return str(address)


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get(
        "x-penflow-client-ip"
    )
    timestamp = request.headers.get(
        "x-penflow-client-time"
    )
    signature = request.headers.get(
        "x-penflow-client-signature"
    )

    if any(
        value is not None
        for value in (forwarded, timestamp, signature)
    ):
        try:
            if not forwarded or not timestamp or not signature:
                raise ValueError(
                    "Incomplete signed headers"
                )

            address = canonical_ip(forwarded)

            if (
                not timestamp.isascii()
                or not timestamp.isdecimal()
                or len(timestamp) != 10
            ):
                raise ValueError("Invalid timestamp")

            if abs(
                int(time.time()) - int(timestamp)
            ) > 60:
                raise ValueError(
                    "Expired forwarding assertion"
                )

            message = (
                f"{timestamp}\n"
                f"{request.method}\n"
                f"{request.url.path}\n"
                f"{forwarded}"
            )

            expected = hmac.new(
                proxy_secret().encode(),
                message.encode(),
                hashlib.sha256,
            ).hexdigest()

            if not hmac.compare_digest(
                signature,
                expected,
            ):
                raise ValueError("Invalid signature")

            return address

        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="Invalid client address assertion",
            ) from exc


    try:
        peer = (
            canonical_ip(request.client.host)
            if request.client
            else "unknown"
        )
    except ValueError:
        peer = "unknown"

    trusted = [
        ipaddress.ip_network(value.strip())
        for value in os.getenv(
            "TRUSTED_PROXY_CIDRS",
            ""
        ).split(",")
        if value.strip()
    ]

    if peer != "unknown" and any(
        ipaddress.ip_address(peer) in network
        for network in trusted
    ):
        chain = request.headers.get(
            "x-forwarded-for",
            "",
        )

        if chain:
            try:
                return canonical_ip(
                    chain.split(",")[-1].strip(),
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid forwarded client address",
                ) from exc

    return peer