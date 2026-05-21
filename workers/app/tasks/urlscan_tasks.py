from typing import Any
from pathlib import Path
from app.queue.celery_app import celery_app
from app.services.urlscan_service import (
    collect_raw_data,
    generate_findings,
    normalize_data,
)

JSONDict = dict[str, Any]


@celery_app.task(name="scan.urlscan")
def run_urlscan(scan_id: str, domain: str) -> JSONDict:
    raw_data = collect_raw_data(domain)
    normalized = normalize_data(raw_data)
    findings = generate_findings(normalized)
    reputation = normalized.get("reputation", {})

    screenshot_path = reputation.get("screenshot_url")

    if screenshot_path and screenshot_path != "default.png":
        reputation["screenshot_path"] = Path(screenshot_path).as_uri()
    else:
        reputation["screenshot_path"] = "default.png"

    status = "failed" if "error" in reputation else "completed"

    return {
        "scan_id": scan_id,
        "source_name": "urlscan",
        "status": status,
        "raw_result": normalized,
        "findings": findings,
        "assets": [],
    }