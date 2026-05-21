from typing import Any

from app.queue.celery_app import celery_app
from app.services.hunter_service import (
    collect_raw_data,
    generate_findings_and_assets,
    normalize_data,
)

JSONDict = dict[str, Any]


@celery_app.task(name="scan.hunter")
def run_hunter(scan_id: str, domain: str) -> JSONDict:
    raw_data = collect_raw_data(domain)
    normalized = normalize_data(raw_data)
    findings, assets = generate_findings_and_assets(normalized)

    return {
        "scan_id": scan_id,
        "source_name": "hunter.io",
        "status": "failed" if "error" in normalized else "completed",
        "raw_result": normalized,
        "findings": findings,
        "assets": assets,
    }