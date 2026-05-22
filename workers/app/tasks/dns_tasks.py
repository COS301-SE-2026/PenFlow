from typing import Any

from app.queue.celery_app import celery_app
from app.services.dns_service import (
    collect_dns_raw_data,
    generate_dns_findings,
    normalize_dns_data,
)
from app.services.whois_service import collect_whois_raw_data

JSONDict = dict[str, Any]


@celery_app.task(name="scan.dns")
def run_dns_scan(scan_id: str, domain: str) -> JSONDict:
    raw_dns = collect_dns_raw_data(domain)
    raw_whois = collect_whois_raw_data(domain)

    normalized_dns = normalize_dns_data(
        raw_dns,
        raw_whois,
    )

    findings = generate_dns_findings(normalized_dns)

    return {
        "scan_id": scan_id,
        "source_name": "dns",
        "status": "failed" if "error" in normalized_dns else "completed",
        "raw_result": normalized_dns,
        "findings": findings,
        "assets": [],
    }