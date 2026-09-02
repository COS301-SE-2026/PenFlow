import json
import re
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import ScanSourceStatus, ScanStatus
from app.models.finding import Finding
from app.models.scan import Scan

SOURCE_ALIASES = {
    "haveibeenpwned": "hibp",
    "urlscanio": "urlscan",
    "httpsecurity": "http_security",
    "tlssecurity": "tls",
    "fingerprinting": "fingerprint",
}

TARGET_EVIDENCE_KEYS = {
    "asset",
    "asset_identifier",
    "domain",
    "email",
    "endpoint",
    "host",
    "hostname",
    "ip",
    "ip_address",
    "port",
    "protocol",
    "service",
    "subdomain",
    "url",
}

def normalize_text(val: object | None) -> str:
    if val is None:
        return ""

    return " ".join(
        str(val).strip().lower().split()
    )


def normalize_source(val: str | None) -> str:
    source = re.sub(
        r"[^a-z0-9]+",
        "",
        normalize_text(val),
    )

    return SOURCE_ALIASES.get(source, source)


def enum_value(val: object) -> str:
    if hasattr(val, "value"):
        return str(val.value)

    return str(val)


def cvss_value(value: Decimal | float | None) -> float | None:
    if value is None:
        return None

    return float(value)


def extract_target_identity(evidence: dict | None) -> str:
    if not isinstance(evidence, dict):
        return ""

    values: list[str] = []

    def visit(value: object) -> None:
        if isinstance(value, dict):
            for key, nested_value in value.items():
                normalized_key = normalize_text(key)

                if normalized_key in TARGET_EVIDENCE_KEYS:
                    serialised = json.dumps(
                        nested_value,
                        sort_keys=True,
                        default=str,
                    )

                    values.append(
                        f"{normalized_key}={serialised.lower()}"
                    )

                elif isinstance(nested_value, (dict,list)):
                    visit(nested_value)

        elif isinstance(value, list):
            for item in value:
                if isinstance(item, (dict, list)):
                    visit(item)

    visit(evidence)

    return "|".join(sorted(set(values)))


def finding_key(finding: Finding) -> str:
    asset_identifer = ""

    if finding.asset is not None:
        asset_identifer = normalize_text(finding.asset.identifier)

    parts = [
        normalize_source(finding.source),
        normalize_text(finding.cve_id),
        normalize_text(finding.title),
        asset_identifer,
        extract_target_identity(finding.evidence),
    ]

    return "::".join(parts)


def changed_fields(
        previous: Finding,
        current: Finding,
) -> list[str]:
    changes: list[str] = []

    if(
        enum_value(previous.severity).lower()
        != enum_value(current.severity).lower()
    ):
        changes.append("severity")

    if(
        cvss_value(previous.cvss_score)
        != cvss_value(current.cvss_score)
    ):
        changes.append("cvss_score")

    if(
        normalize_text(previous.description)
        != normalize_text(current.description)
    ):
        changes.append("description")

    if(
        normalize_text(previous.recommendation)
        != normalize_text(current.recommendation)
    ):
        changes.append("recommendation")

    return changes


def finding_to_report_item(finding: Finding) -> dict:
    return {
        "id": str(finding.id),
        "title": finding.title,
        "source": finding.source,
        "severity": enum_value(finding.severity).lower(),
        "status": enum_value(finding.status).lower(),
        "cve_id": finding.cve_id,
        "cvss_score": cvss_value(finding.cvss_score),
        "description": finding.description,
        "recommendation": finding.recommendation,
        "asset_identifier": (
            finding.asset.identifier
            if finding.asset is not None
            else None
        ),
    }


async def load_scan_for_delta(
        db: AsyncSession,
        scan_id: UUID,
) -> Scan | None:
    result = await db.execute(
        select(Scan).options(
            selectinload(Scan.findings).selectinload(
                Finding.asset,
            ),
            selectinload(Scan.sources),
        ).where(Scan.id == scan_id)
    )

    return result.scalar_one_or_none()


async def load_previous_completed_scan(
        db: AsyncSession,
        current_scan: Scan,
) -> Scan | None:
    if current_scan.schedule_id is None:
        return None

    query = (
        select(Scan).options(
            selectinload(Scan.findings).selectinload(
                Finding.asset,
            ),
            selectinload(Scan.sources),
        ).where(
            Scan.schedule_id == current_scan.schedule_id,
            Scan.id != current_scan.id,
            Scan.status == ScanStatus.COMPLETED,
        )
    )

    if current_scan.scheduled_for is not None:
        query = query.where(
            Scan.scheduled_for < current_scan.scheduled_for,
        )

    else:
        query = query.where(
            Scan.created_at < current_scan.created_at,
        )

    query = (
        query.order_by(
            Scan.scheduled_for.desc().nullslast(),
            Scan.completed_at.desc().nullslast(),
            Scan.created_at.desc(),
        ).limit(1)
    )

    result = await db.execute(query)
    return result.scalar_one_or_none()


def baseline_result(
        current_scan: Scan,
        reason: str,
) -> dict:
    findings = [
        finding_to_report_item(finding)
        for finding in current_scan.findings
    ]

    return {
        "is_baseline": True,
        "reason": reason,
        "current_scan_id": str(current_scan.id),
        "previous_scan_id": None,
        "previous_completed_at": None,
        "summary": {
            "baseline": len(findings),
            "new": 0,
            "resolved": 0,
            "changed": 0,
            "unchanged": 0,
            "not_evaluated": 0,
        },
        "baseline_findings": findings,
        "new_findings": [],
        "resolved_findings": [],
        "changed_findings": [],
        "unchanged_findings": [],
        "not_evaluated_findings": [],
    }


async def build_scan_delta(
        db: AsyncSession,
        current_scan_id: UUID,
) -> dict:
    current_scan = await load_scan_for_delta(
        db,
        current_scan_id,
    )

    if current_scan is None:
        raise ValueError(f"Scan not found {current_scan_id}")

    if current_scan.status not in {
        ScanStatus.COMPLETED,
        ScanStatus.PARTIAL,
    }:
        raise ValueError("Delta reporting requires a completed or partial scan")

    if current_scan.schedule_id is None:
        return baseline_result(
            current_scan,
            reason="This scan was not created by a recurring schedule"
        )

    previous_scan = await load_previous_completed_scan(
        db,
        current_scan,
    )

    if previous_scan is None:
        return baseline_result(
            current_scan,
            reason="This is the first completed scan for the schedule",
        )

    current_findings = {
        finding_key(finding): finding
        for finding in current_scan.findings
    }

    previous_findings = {
        finding_key(finding): finding
        for finding in previous_scan.findings
    }

    current_keys = set(current_findings)
    previous_keys = set(previous_findings)

    new_keys = current_keys - previous_keys
    missing_keys = previous_keys - current_keys
    shared_keys = current_keys & previous_keys

    completed_sources = {
        normalize_source(source.source_name)
        for source in current_scan.sources
        if source.status == ScanSourceStatus.COMPLETED
    }

    new_items = [
        finding_to_report_item(current_findings[key])
        for key in sorted(new_keys)
    ]

    resolved_items = []
    not_evaluated_items = []

    for key in sorted(missing_keys):
        finding = previous_findings[key]
        source = normalize_source(finding.source)

        if source in completed_sources:
            resolved_items.append(
                finding_to_report_item(finding)
            )

        else:
            not_evaluated_items.append(
                finding_to_report_item(finding)
            )

    changed_items = []
    unchanged_items = []

    for key in sorted(shared_keys):
        previous = previous_findings[key]
        current = current_findings[key]

        changes = changed_fields(
            previous,
            current,
        )

        if changes:
            changed_items.append(
                {
                    "finding": finding_to_report_item(current),
                    "previous_severity": enum_value(
                        previous.severity
                    ).lower(),
                    "current_severity": enum_value(
                        current.severity,
                    ).lower(),
                    "changed_fields": changes,
                }
            )
        else:
            unchanged_items.append(
                finding_to_report_item(current)
            )

    return {
        "is_baseline": False,
        "reason": None,
        "current_scan_id": str(current_scan.id),
        "previous_scan_id": str(previous_scan.id),
        "previous_completed_at": previous_scan.completed_at,
        "summary": {
            "baseline": 0,
            "new": len(new_items),
            "resolved": len(resolved_items),
            "changed": len(changed_items),
            "unchanged": len(unchanged_items),
            "not_evaluated": len(not_evaluated_items),
        },
        "baseline_findings": [],
        "new_findings": new_items,
        "resolved_findings": resolved_items,
        "changed_findings": changed_items,
        "unchanged_findings": unchanged_items,
        "not_evaluated_findings": not_evaluated_items,
    }

