from app.queue.celery_app import celery_app

from app.services.dns_service import (
    collect_dns_raw_data,
    normalize_dns_data,
    generate_dns_findings,
)

from app.services.whois_service import collect_whois_raw_data


@celery_app.task
def run_dns_scan(domain: str):
    raw_dns = collect_dns_raw_data(domain)

    raw_whois = collect_whois_raw_data(domain)

    normalized_dns = normalize_dns_data(
        raw_dns,
        raw_whois,
    )

    findings = generate_dns_findings(normalized_dns)

    return {
        "source_name": "dns",
        "status": "completed",
        "raw_result": normalized_dns,
        "findings": findings,
        "assets": [],
    }