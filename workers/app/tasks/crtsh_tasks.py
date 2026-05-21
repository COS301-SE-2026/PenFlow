from typing import Any

from app.queue.celery_app import celery_app
from app.services.crt_sh_service import (
    collect_raw_data,
    generate_findings_and_assets,
    normalize_data,
)

JSONDict = dict[str, Any]


@celery_app.task(name="scan.crt_sh")
def run_crt_sh(scan_id: str, domain: str) -> JSONDict:
    raw_data = collect_raw_data(domain)
    normalized = normalize_data(raw_data)
    findings, assets = generate_findings_and_assets(normalized)
    subdomains = normalized.get("subdomains", {})
    status = "failed" if "error" in subdomains else "completed"

    return {
        "scan_id": scan_id,
        "source_name": "crt.sh",
        "status": status,
        "raw_result": normalized,
        "findings": findings,
        "assets": assets,
    }