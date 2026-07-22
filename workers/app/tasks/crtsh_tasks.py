from typing import Any
import json
import redis

from app.queue.celery_app import celery_app
from app.services.crt_sh_service import (
    collect_raw_data,
    generate_findings_and_assets,
    normalize_data,
)
from app.utils.callback import send_source_callback

JSONDict = dict[str, Any]
redis_client = redis.Redis(host='penflow-redis', port=6379, db=0)


@celery_app.task(name="scan.crt_sh")
def run_crt_sh(scan_id: str, domain: str) -> JSONDict:
    try:
        raw_data = collect_raw_data(domain)
        normalized = normalize_data(raw_data)
        findings, assets = generate_findings_and_assets(normalized)
        subdomains = normalized.get("subdomains", {})
        status = "failed" if "error" in subdomains else "completed"

        result = {
            "scan_id": scan_id,
            "source_name": "crt.sh",
            "status": status,
            "raw_result": normalized,
            "findings": findings,
            "assets": assets,
        }

        redis_client.publish(f"scan_stream_{scan_id}", json.dumps({
            "scan_id": scan_id, "progress": 30, "status": status,
            "source": "crt.sh", "message": "SSL Certificate Search completed"
        }))

    except Exception as error:
        result = {
            "scan_id": scan_id,
            "source_name": "crt.sh",
            "status": "failed",
            "raw_result": {"error": str(error)},
            "findings": [],
            "assets": [],
            "error_message": str(error),
        }
        redis_client.publish(f"scan_stream_{scan_id}", json.dumps({
            "scan_id": scan_id, "progress": 30, "status": "failed",
            "source": "crt.sh", "message": f"SSL Search failed: {str(error)}"
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

