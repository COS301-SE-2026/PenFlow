from typing import Any
import json
import redis

from app.queue.celery_app import celery_app
from app.services.dns_service import (
    collect_dns_raw_data,
    generate_dns_findings,
    normalize_dns_data,
)
from app.services.whois_service import collect_whois_raw_data
from app.utils.callback import send_source_callback

JSONDict = dict[str, Any]
redis_client = redis.Redis(host="penflow-redis", port=6379, db=0)


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
            "findings": findings,
            "assets": [],
        }

        redis_client.publish(f"scan_stream_{scan_id}", json.dumps({
            "scan_id": scan_id, "progress": 15, "status": status,
            "source": "dns", "message": "DNS & WHOIS Enumeration completed"
        }))

    except Exception as error:
        result = {
            "scan_id": scan_id,
            "source_name": "dns",
            "status": "failed",
            "raw_result": {"error": str(error)},
            "findings": [],
            "assets": [],
            "error_message": str(error),
        }
        redis_client.publish(f"scan_stream_{scan_id}", json.dumps({
            "scan_id": scan_id, "progress": 15, "status": "failed",
            "source": "dns", "message": f"DNS Enumeration failed: {str(error)}"
        }))

    send_source_callback(
        scan_id=scan_id,
        source_name=result["source_name"],
        status=result["status"],
        raw_result=result["raw_result"],
        findings=result["findings"],
        assets=result["assets"],
        error_message=result.get("error_message"),
    )

    return result