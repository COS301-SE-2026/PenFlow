import json
from typing import Any

import redis

from app.queue.celery_app import celery_app
from app.services.wappalyzer_service import (
    collect_raw_data,
    generate_findings_and_assets,
    normalize_data,
)
from app.utils.callback import send_source_callback

JSONDict = dict[str, Any]
redis_client = redis.Redis(host="penflow-redis", port=6379, db=0)


@celery_app.task(name="scan.wappalyzer")
def run_wappalyzer(scan_id: str, domain: str) -> JSONDict:
    try:
        raw_data = collect_raw_data(domain)
        normalized = normalize_data(raw_data)
        findings, assets = generate_findings_and_assets(normalized)

        status = "failed" if "error" in normalized else "completed"

        result = {
            "scan_id": scan_id,
            "source_name": "wappalyzer",
            "status": status,
            "raw_result": {"tech_stack": normalized},
            "findings": findings,
            "assets": assets,
        }

        redis_client.publish(
            f"scan_stream_{scan_id}",
            json.dumps(
                {
                    "scan_id": scan_id,
                    "progress": 45,
                    "status": status,
                    "source": "wappalyzer",
                    "message": "Technology Stack Analysis completed",
                }
            ),
        )

    except Exception as error:
        result = {
            "scan_id": scan_id,
            "source_name": "wappalyzer",
            "status": "failed",
            "raw_result": {"error": str(error)},
            "findings": [],
            "assets": [],
            "error_message": str(error),
        }
        redis_client.publish(
            f"scan_stream_{scan_id}",
            json.dumps(
                {
                    "scan_id": scan_id,
                    "progress": 45,
                    "status": "failed",
                    "source": "wappalyzer",
                    "message": f"Tech Stack Analysis failed: {str(error)}",
                }
            ),
        )

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
