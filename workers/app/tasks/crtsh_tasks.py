from typing import Any

from app.queue.celery_app import celery_app
from app.services.crt_sh_service import (
    collect_raw_data,
    generate_findings_and_assets,
    normalize_data,
)
from app.utils.callback import send_source_callback

JSONDict = dict[str, Any]

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
            "assets": assets,
            "services": [],
            "technologies": [],
            "findings": findings,
        }

    except Exception as error:
        result = {
            "scan_id": scan_id,
            "source_name": "crt.sh",
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
