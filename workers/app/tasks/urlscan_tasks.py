import logging
from typing import Any

from app.queue.celery_app import celery_app
from app.services.urlscan_service import (
    collect_raw_data,
    generate_findings,
    normalize_data,
)
from app.utils.callback import send_source_callback
logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]

@celery_app.task(name="scan.urlscan")
def run_urlscan(scan_id: str, domain: str) -> JSONDict:
    try:
        send_source_callback(scan_id=scan_id, source_name="urlscan", status="running")
    except Exception:
        logger.warning("[URLScan_Task] Failed to send `running` callback for %s",scan_id)

    try:
        raw_data = collect_raw_data(domain)
        normalized = normalize_data(raw_data)
        findings = generate_findings(normalized)
        reputation = normalized.get("reputation", {})

        screenshot_path = reputation.get("screenshot_url")

        if screenshot_path and screenshot_path != "default.png":
            reputation["screenshot_path"] = screenshot_path
        else:
            reputation["screenshot_path"] = "default.png"

        status = "failed" if "error" in reputation else "completed"

        result = {
            "scan_id": scan_id,
            "source_name": "urlscan",
            "status": status,
            "raw_result": normalized,
            "findings": findings,
            "assets": [],
        }

    except Exception as error:
        result = {
            "scan_id": scan_id,
            "source_name": "urlscan",
            "status": "failed",
            "raw_result": {"error": str(error)},
            "findings": [],
            "assets": [],
            "error_message": str(error),
        }

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
