from typing import Any

from app.queue.celery_app import celery_app
from app.services.urlscan_service import (
    collect_raw_data,
    generate_findings,
    normalize_data,
)
from app.utils.callback import send_source_callback

JSONDict = dict[str, Any]

@celery_app.task(name="scan.urlscan")
def run_urlscan(scan_id: str, domain: str) -> JSONDict:
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
            "assets": [],
            "services": [],
            "technologies": [],
            "findings": findings,
        }

    except Exception as error:
        result = {
            "scan_id": scan_id,
            "source_name": "urlscan",
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
