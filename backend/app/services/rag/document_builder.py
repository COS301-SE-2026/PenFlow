from enum import Enum
from typing import Any

from app.models.finding import Finding

FINDING_DOCUMENT_SCHEMA_VERSION = "finding-v1"


def display(value: Any, fallback: str = "Not provided") -> str:
    if value is None:
        return fallback

    if isinstance(value, Enum):
        return str(value.value)

    text = str(value).strip()
    return text if text else fallback


def build_finding_text(finding: Finding) -> str:
    scan = finding.scan
    asset = finding.asset
    service = finding.service

    lines = [
        f"Finding ID: {finding.id}",
        f"Title: {display(finding.title)}",
        f"Severity: {display(finding.severity)}",
        f"CVSS score: {display(finding.cvss_score)}",
        f"CVE: {display(finding.cve_id)}",
        f"Status: {display(finding.status)}",
        f"Verified: {'Yes' if finding.is_verified else 'No'}",
        f"Source: {display(finding.source)}",
        f"Domain: {display(scan.domain if scan else None)}",
        f"Asset: {display(asset.identifier if asset else None)}",
        f"Asset type: {display(asset.asset_type if asset else None)}",
        f"Service host: {display(service.host if service else None)}",
        f"Service port: {display(service.port if service else None)}",
        f"Protocol: {display(service.protocol if service else None)}",
        f"Service name: {display(service.service_name if service else None)}",
        f"Product: {display(service.product if service else None)}",
        f"Product version: {display(service.version if service else None)}",
        "",
        "Description:",
        display(finding.description),
        "",
        "Recommendation:",
        display(finding.recommendation),
    ]

    return "\n".join(lines)