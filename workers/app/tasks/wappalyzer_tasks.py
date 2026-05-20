from typing import Any

from app.queue.celery_app import celery_app
from app.services.wappalyzer_service import (
    collect_raw_data,
    generate_findings_and_assets,
    normalize_data,
)

JSONDict = dict[str, Any]


@celery_app.task(name="scan.wappalyzer")
def run_wappalyzer(scan_id: str, domain: str) -> JSONDict:
    raw_data = collect_raw_data(domain)
    normalized = normalize_data(raw_data)
    findings, assets = generate_findings_and_assets(normalized)

    return {
        "scan_id": scan_id,
        "source_name": "wappalyzer",
        "status": "failed" if "error" in normalized else "completed",
        "raw_result": {"tech_stack": normalized},
        "findings": findings,
        "assets": assets,
    }