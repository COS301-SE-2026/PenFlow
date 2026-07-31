from typing import Any

from app.queue.celery_app import celery_app
from app.services.dns_service import (
    collect_dns_raw_data,
    generate_dns_findings,
    normalize_dns_data,
)
from app.services.whois_service import collect_whois_raw_data
from app.utils.callback import send_source_callback

JSONDict = dict[str, Any]

@celery_app.task(name="scan.dns")
def run_dns_scan(scan_id: str, domain: str) -> JSONDict:
    try:
        raw_dns = collect_dns_raw_data(domain)
        raw_whois = collect_whois_raw_data(domain)

        normalized_dns = normalize_dns_data(
            raw_dns,
            raw_whois,
        )

        findings = generate_dns_findings(normalized_dns)

        status = "failed" if "error" in normalized_dns else "completed"

        result = {
            "scan_id": scan_id,
            "source_name": "dns",
            "status": status,
            "raw_result": normalized_dns,
            "assets": [],
            "services": [],
            "technologies": [],
            "findings": findings,
        }

    except Exception as error:
        result = {
            "scan_id": scan_id,
            "source_name": "dns",
            "status": "failed",
            "raw_result": {"error": str(error)},
            "assets": [],
            "services": [],
            "technologies": [],
            "findings": [],
            "error_message": str(error),
        }

    send_source_callback(
        scan_id=scan_id,
        source_name=result["source_name"],
        status=result["status"],
        raw_result=result["raw_result"],
        assets=result["assets"],
        services=result["services"],
        technologies=result["technologies"],
        findings=result["findings"],
        error_message=result.get("error_message"),
    )

    return result
