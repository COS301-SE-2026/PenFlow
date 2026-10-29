import json
from enum import Enum
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.finding import Finding
from app.models.scan import Scan
from app.models.scan_source import ScanSource
from app.models.service import Service
from app.services.assistant_scan_details import (
    DETAIL_RULES,
    collect_scan_details,
)
from app.services.rag.generation_provider import GenerationProvider

SEVERITIES = ("critical", "high", "medium", "low", "info")

SOURCE_NAMES = frozenset({
    "dns",
    "crt.sh",
    "urlscan",
    "wappalyzer",
    "shodan",
    "hibp",
    "hunter.io",
    "target_resolution",
    "nmap",
    "http_security",
    "tls",
    "fingerprint",
    "cpe_resolver",
    "cve",
})

SOURCE_STATES = frozenset({
    "pending", "running", "completed", "failed", "partial", "skipped",
})

SCAN_STATES = frozenset({
    "queued", "running", "completed", "failed", "partial",
})

SNAPSHOT_RULES = """
The scan_overview JSON is an aggregate snapshot of the selected authorized scan.
Counts describe stored records, not necessarily open findings or unique hosts.
It contains no individual asset, service or finding details.
Missing details in retrieved evidence do not mean the scan has no such records.
Only a zero count establishes that no records were recorded for that category
at collection time. A running scan may still add records.
Use detailed evidence for individual claims, severity, CVEs and citations.
The overview does not authorize new identifiers, links or finding citations.
Do not invent configuration steps or claim a database query was performed by you.
If needed details were not supplied, say so; do not claim records do not exist.
Keep the required response format and citation rules unchanged.
""".strip()


def enum_text(value: object) -> str:
    return (
        str(value.value)
        if isinstance(value, Enum)
        else str(value)
    )


async def collect_scan_snapshot(
    db: AsyncSession,
    scan_id: UUID,
) -> str:
    status = await db.scalar(
        select(Scan.status).where(Scan.id == scan_id)
    )

    if status is None:
        raise HTTPException(
            status_code=404,
            detail="Scan not found.",
        )

    totals = (
        (
            await db.execute(
                select(
                    select(func.count())
                    .select_from(Asset)
                    .where(Asset.scan_id == scan_id)
                    .scalar_subquery()
                    .label("assets"),

                    select(func.count())
                    .select_from(Service)
                    .where(Service.scan_id == scan_id)
                    .scalar_subquery()
                    .label("services"),

                    select(func.count())
                    .select_from(Finding)
                    .where(Finding.scan_id == scan_id)
                    .scalar_subquery()
                    .label("findings"),
                )
            )
        )
        .mappings()
        .one()
    )

    severity_rows = (
        await db.execute(
            select(Finding.severity, func.count())
            .where(Finding.scan_id == scan_id)
            .group_by(Finding.severity)
        )
    ).all()

    severity_counts = dict.fromkeys(SEVERITIES, 0)
    other_severity = 0

    for severity, count in severity_rows:
        name = enum_text(severity)

        if name in severity_counts:
            severity_counts[name] += int(count)
        else:
            other_severity += int(count)

    source_rows = (
        await db.execute(
            select(
                ScanSource.source_name,
                ScanSource.status,
            )
            .where(ScanSource.scan_id == scan_id)
            .order_by(ScanSource.source_name)
        )
    ).all()

    source_statuses: dict[str, str] = {}
    other_sources = 0

    for name, source_status in source_rows:
        # Never send arbitrary database labels externally.
        if name in SOURCE_NAMES:
            value = enum_text(source_status)
            source_statuses[name] = (
                value if value in SOURCE_STATES else "unknown"
            )
        else:
            other_sources += 1

    state = enum_text(status)

    return json.dumps(
        {
            "scan_overview": {
                "scan_status": (
                    state if state in SCAN_STATES else "unknown"
                ),
                "record_counts": {
                    key: int(totals[key])
                    for key in ("assets", "services", "findings")
                },
                "finding_severity_counts": severity_counts,
                "other_severity_count": other_severity,
                "source_statuses": source_statuses,
                "other_source_count": other_sources,
                "individual_record_details": (
                    "not_included_in_overview"
                ),
                "consistency": (
                    "live_read_counts_may_change_during_scan"
                ),
            },
        },
        sort_keys=True,
    )


class ScanAwareGenerationProvider:

    def __init__(
        self,
        provider: GenerationProvider,
        db: AsyncSession,
        scan_id: UUID,
        *,
        question: str = "",
    ) -> None:
        self.provider = provider
        self.db = db
        self.scan_id = scan_id
        self.model = provider.model
        self.question = question

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        snapshot = await collect_scan_snapshot(
            self.db,
            self.scan_id,
        )

        details = await collect_scan_details(
            self.db,
            self.scan_id,
            self.question,
        )

        extra_rules = (
            f"\n\n{DETAIL_RULES}" if details else ""
        )

        context = (
            f"{snapshot}\n\n{details}"
            if details
            else snapshot
        )

        return await self.provider.generate(
            system_prompt=(
                f"{system_prompt}\n\n"
                f"{SNAPSHOT_RULES}{extra_rules}"
            ),
            user_prompt=f"{context}\n\n{user_prompt}",
        )