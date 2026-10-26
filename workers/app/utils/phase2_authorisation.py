import time
from datetime import datetime, timezone
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

import httpx

from app.utils.callback import build_api_url
from app.utils.internal_auth import internal_headers
from app.utils.internal_http import internal_http_options
from app.utils.safe_outbound import (
    normalise_host,
    public_ip,
    resolve_public_host,
)


def check_scope(
        permission: dict,
        targets: list[dict],
        stage: str,
        profile: str,      
) -> None:
    grant = permission["authorisation"]
    root = normalise_host(permission["domain"])

    if (
        grant["scope"]["domain"] != root
        or grant["scope"]["nmap_profile"] != profile
    ):
        raise ValueError("Authorisation scope mismatch")

    deadline = time.monotonic() + 20.0

    for target in targets:
        host = normalise_host(target["hostname"])

        if host != root and not host.endswith("." + root):
            raise ValueError(
                "Hostname is outside authorised scope"
            )

        addresses = [
            *target.get("ipv4", []),
            *target.get("ipv6", []),
        ]

        if stage in {"bootstrap", "resolve"}:
            continue

        if not addresses and stage == "pipeline":
            continue

        if not addresses and stage in {
            "nmap",
            "tls",
            "http_security",
        }:
            raise ValueError(
                "A pinned target address is required"
            )

        remaining = deadline - time.monotonic()

        if remaining <= 0:
            raise ValueError("Scope validation timed out")

        current = set(
            resolve_public_host(
                host,
                timeout=min(5.0, remaining),
            )
        )

        if not current:
            raise ValueError("Target has no public addresses")

        if any(
            public_ip(value) not in current
            for value in addresses
        ):
            raise ValueError(
                "Target IP no longer resolves from the authorised hostname"
            )


    expires = datetime.fromisoformat(grant["expires_at"])

    if expires.tzinfo is None or datetime.now(timezone.utc) >= expires:
        raise ValueError("Scan authorisation expired")


def require_phase2_authorisation(
        scan_id: str,
        *,
        stage: str,
        domain: str | None = None,
        targets: list[dict] | None = None,
        profile: str = "standard",
) -> dict[str, Any]:
    scan_id = str(UUID(str(scan_id)))

    cleaned = [
        {
            "hostname": item["hostname"],
            "ipv4": item.get("ipv4", []),
            "ipv6": item.get("ipv6", []),
        }
        for item in (targets or [])
    ]

    payload = {
        "stage": stage,
        "domain": domain,
        "targets": cleaned,
        "profile": profile,
    }

    url = build_api_url(
        f"/internal/scans/{scan_id}/authorise-execution"
    )

    # Prevents race conditions with a scheduled job that might reach the queue before its DB commit
    with httpx.Client(
        timeout=30.0,
        **internal_http_options(url),
    ) as client:
        for attempt in range(4):
            response = client.post(
                url,
                headers=internal_headers(),
                json=payload,
            )

            if response.status_code != 404 or attempt == 3:
                break

            time.sleep(attempt + 1)

        response.raise_for_status()
        permission = response.json()

    check_scope(
        permission,
        cleaned,
        stage,
        profile,
    )

    return permission


def authorise_operation(
        payload: dict,
        stage: str,
) -> dict:
    if stage == "nmap":
        hosts = payload.get("hostnames", [])

        if not hosts:
            raise ValueError(
                "Nmap requires scoped hostnames"
            )

    elif stage == "fingerprint":
        parsed = urlsplit(payload["target_url"])

        if (
            parsed.scheme not in {"http", "https"}
            or parsed.username
            or not parsed.hostname
        ):
            raise ValueError(
                "Invalid fingerprint target URL"
            )

        hosts = [parsed.hostname]

    else:
        hosts = [payload["hostname"]]

    address = payload.get("ip_address")
    targets = []

    for host in hosts:
        target = {
            "hostname": host,
            "ipv4": [],
            "ipv6": [],
        }

        if address is not None:
            version = ip_address(
                public_ip(address)
            ).version
            target[f"ipv{version}"] = [address]

        targets.append(target)

    return require_phase2_authorisation(
        payload["scan_id"],
        stage=stage,
        targets=targets,
        profile=payload.get("profile", "standard"),
    )