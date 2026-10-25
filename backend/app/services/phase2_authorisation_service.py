from datetime import datetime, timedelta, timezone
from ipaddress import ip_address
from typing import Any, Literal
from uuid import UUID, uuid4

import idna
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.domain_service import DomainService

AUTHORISATION_VERSION = 1
AUTHORISATION_VALIDITY = timedelta(days=30)

Source = Literal["manual_scan", "schedule"]


def normalise_domain(value: str) -> str:
    value = value.strip().rstrip(".")

    try:
        host = idna.encode(
            value,
            uts46=True,
            std3_rules=True,
        ).decode("ascii").lower()
    except idna.IDNAError as exc:
        raise HTTPException(422, "Invalid domain") from exc

    if "." not in host or len(host) > 253:
        raise HTTPException(422, "A valid domain is required")

    try:
        ip_address(host)
    except ValueError:
        return host

    raise HTTPException(422, "A domain name is required")


class Phase2AuthorisationService:
    @staticmethod
    async def issue(
        db: AsyncSession,
        *,
        user_id: UUID,
        verified_domain_id: UUID,
        domain: str,
        source: Source,
    ) -> dict[str, Any]:
        expected_domain = normalise_domain(domain)

        verified = await DomainService.verify_domain(
            db,
            domain_id=verified_domain_id,
            user_id=user_id,
        )

        if normalise_domain(verified.domain) != expected_domain:
            raise HTTPException(
                400,
                "Domain does not match the verified domain record",
            )

        now = datetime.now(timezone.utc)

        return {
            "id": str(uuid4()),
            "version": AUTHORISATION_VERSION,
            "actor_user_id": str(user_id),
            "verified_domain_id": str(verified_domain_id),
            "source": source,
            "issued_at": now.isoformat(),
            "expires_at": (now + AUTHORISATION_VALIDITY).isoformat(),
            "ownership_checked_at": verified.last_checked_at.isoformat(),
            "scope": {
                "domain": expected_domain,
                "include_subdomains": True,
                "nmap_profile": "standard",
                "network_scope": (
                    "public_addresses_resolved_from_scoped_hostnames"
                ),
            },
        }

    @staticmethod
    def validate(
        record: object,
        *,
        user_id: UUID,
        verified_domain_id: UUID,
        domain: str,
    ) -> dict[str, Any]:
        if not isinstance(record, dict):
            raise HTTPException(
                403,
                "Active scan authorisation is missing",
            )

        try:
            scope = record["scope"]
            issued_at = datetime.fromisoformat(record["issued_at"])
            expires_at = datetime.fromisoformat(record["expires_at"])

            valid = (
                record["version"] == AUTHORISATION_VERSION
                and UUID(record["id"]) is not None
                and record["actor_user_id"] == str(user_id)
                and record["verified_domain_id"] == str(verified_domain_id)
                and record["source"] in {"manual_scan", "schedule"}
                and isinstance(scope, dict)
                and scope["domain"] == normalise_domain(domain)
                and scope["include_subdomains"] is True
                and scope["nmap_profile"] == "standard"
                and scope["network_scope"]
                == "public_addresses_resolved_from_scoped_hostnames"
                and issued_at.tzinfo is not None
                and expires_at.tzinfo is not None
            )

            if not valid:
                raise ValueError("Invalid authorisation")

            now = datetime.now(timezone.utc)

            if not (
                issued_at <= now < expires_at
                and timedelta(0)
                < expires_at - issued_at
                <= AUTHORISATION_VALIDITY
            ):
                raise ValueError("Authorisation expired or invalid")

        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise HTTPException(
                403,
                "Active scan authorisation is expired or invalid",
            ) from exc

        return record