from typing import Any

from app.utils.callback import send_source_callback
from app.queue.celery_app import celery_app
from app.services.hunter_service import (
    collect_raw_data,
    generate_findings_and_assets,
    normalize_data,
)

JSONDict = dict[str, Any]


@celery_app.task(name="scan.hunter")
def run_hunter(scan_id: str, domain: str) -> JSONDict:
    try:
        raw_data = collect_raw_data(domain)
        normalized = normalize_data(raw_data)
        findings, assets = generate_findings_and_assets(normalized)

        status = "failed" if "error" in normalized else "completed"

        result = {
            "scan_id": scan_id,
            "source_name": "hunter.io",
            "status": status,
            "raw_result": normalized,
            "findings": findings,
            "assets": assets,
        }
    
    except Exception as error:
        result = {
            "scan_id": scan_id,
            "source_name": "hunter.io",
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