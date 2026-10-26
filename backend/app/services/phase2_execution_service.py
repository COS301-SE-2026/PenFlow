from copy import deepcopy
from datetime import datetime, timezone
from ipaddress import ip_address
from typing import Any, Literal
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import ScanStatus, ScanType
from app.models.scan import Scan
from app.models.scan_schedule import ScanSchedule
from app.services.domain_service import DomainService
from app.services.phase2_authorisation_service import (
    Phase2AuthorisationService,
    normalise_domain,
)

Stage = Literal[
    "bootstrap",
    "resolve",
    "pipeline",
    "nmap",
    "http_security",
    "tls",
    "fingerprint",
]


class ExecutionTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hostname: str = Field(min_length=1, max_length=253)
    ipv4: list[str] = Field(default_factory=list, max_length=2)
    ipv6: list[str] = Field(default_factory=list, max_length=2)


class ExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: Stage
    domain: str | None = Field(default=None, max_length=253)
    profile: Literal["standard"] = "standard"
    targets: list[ExecutionTarget] = Field(
        default_factory=list,
        max_length=10,
    )


def checked_targets(
    request: ExecutionRequest,
    domain: str,
) -> list[dict[str, Any]]:
    result = []

    for target in request.targets:
        hostname = normalise_domain(target.hostname)

        if hostname != domain and not hostname.endswith("." + domain):
            raise HTTPException(
                403,
                "Hostname is outside authorised scope",
            )

        record: dict[str, Any] = {
            "hostname": hostname,
            "ipv4": [],
            "ipv6": [],
        }

        for version, values in (
            (4, target.ipv4),
            (6, target.ipv6),
        ):
            for value in values:
                try:
                    address = ip_address(value)
                except ValueError as exc:
                    raise HTTPException(
                        403,
                        "Invalid target address",
                    ) from exc

                if (
                    address.version != version
                    or not address.is_global
                    or address.is_multicast
                    or address.is_reserved
                    or getattr(address, "ipv4_mapped", None) is not None
                    or "%" in value
                ):
                    raise HTTPException(
                        403,
                        "Target address is not public",
                    )

                record[f"ipv{version}"].append(str(address))

        result.append(record)

    if request.stage not in {"bootstrap", "pipeline"} and not result:
        raise HTTPException(403, "Target scope is required")

    return result


class Phase2ExecutionService:
    @staticmethod
    async def authorise(
        db: AsyncSession,
        scan_id: UUID,
        request: ExecutionRequest,
    ) -> dict[str, Any]:
        scan = await db.scalar(
            select(Scan).where(Scan.id == scan_id)
        )

        if scan is None:
            raise HTTPException(404, "Scan not found")

        if scan.scan_type != ScanType.ACTIVE_VULNERABILITY:
            raise HTTPException(403, "Phase 2 scan required")

        if scan.status not in {
            ScanStatus.QUEUED,
            ScanStatus.RUNNING,
        }:
            raise HTTPException(
                409,
                "Scan is no longer executable",
            )

        schedule = None

        if scan.schedule_id is not None:
            schedule = await db.get(
                ScanSchedule,
                scan.schedule_id,
            )

        try:
            if scan.user_id is None or scan.verified_domain_id is None:
                raise HTTPException(
                    403,
                    "Scan ownership record is missing",
                )

            record = Phase2AuthorisationService.validate(
                scan.authorisation,
                user_id=scan.user_id,
                verified_domain_id=scan.verified_domain_id,
                domain=scan.domain,
            )

            domain = record["scope"]["domain"]

            if (
                request.domain is not None
                and normalise_domain(request.domain) != domain
            ):
                raise HTTPException(
                    403,
                    "Scan domain does not match",
                )

            if request.profile != record["scope"]["nmap_profile"]:
                raise HTTPException(
                    403,
                    "Scan profile does not match",
                )

            if record["source"] == "schedule" or scan.schedule_id is not None:
                if (
                    schedule is None
                    or not schedule.is_active
                    or schedule.user_id != scan.user_id
                    or schedule.verified_domain_id != scan.verified_domain_id
                    or record["source"] != "schedule"
                ):
                    raise HTTPException(
                        403,
                        "Schedule is no longer authorised",
                    )

                live = Phase2AuthorisationService.validate(
                    schedule.authorisation,
                    user_id=scan.user_id,
                    verified_domain_id=scan.verified_domain_id,
                    domain=scan.domain,
                )

                if live["id"] != record["id"]:
                    raise HTTPException(
                        403,
                        "Schedule authorisation was replaced",
                    )

            targets = checked_targets(request, domain)

            await DomainService.verify_domain(
                db,
                domain_id=scan.verified_domain_id,
                user_id=scan.user_id,
                commit=False,
            )

            Phase2AuthorisationService.validate(
                record,
                user_id=scan.user_id,
                verified_domain_id=scan.verified_domain_id,
                domain=scan.domain,
            )

            snapshot = deepcopy(record)
            snapshot["last_execution_check"] = {
                "at": datetime.now(timezone.utc).isoformat(),
                "stage": request.stage,
                "requested_targets": targets,
                "decision": "ownership_and_authorisation_valid",
            }

            scan.authorisation = snapshot
            await db.commit()

            return {
                "domain": domain,
                "authorisation": snapshot,
                "targets": targets,
            }

        except HTTPException as exc:
            if schedule is not None and schedule.user_id == scan.user_id:
                schedule.is_active = False

            await db.commit()

            raise HTTPException(
                403,
                "Phase 2 execution authorisation failed",
            ) from exc

        except Exception:
            await db.rollback()
            raise