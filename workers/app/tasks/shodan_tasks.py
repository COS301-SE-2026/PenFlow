import logging
from typing import Any

from app.queue.celery_app import celery_app
from app.services.shodan_service import (
    collect_raw_data,
    generate_findings_and_assets,
    normalize_data,
)
from app.utils.callback import send_source_callback

logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]


@celery_app.task(name="scan.shodan")
def run_shodan(scan_id: str, domain: str) -> JSONDict:
    try:
        send_source_callback(scan_id=scan_id, source_name="shodan", status="running")
    except Exception:
        logger.warning("[SHODAN_Task] Failed to send `running` callback for %s",scan_id)

    try:
        raw_data = collect_raw_data(domain)
        normalized = normalize_data(raw_data)
        findings, assets = generate_findings_and_assets(normalized)

        status = "failed" if "error" in normalized else "completed"

        result = {
            "scan_id": scan_id,
            "source_name": "shodan",
            "status": status,
            "raw_result": {"infrastructure": normalized},
            "assets": assets,
            "services": [],
            "technologies": [],
            "findings": findings,
        }

    except Exception as error:
        result = {
            "scan_id": scan_id,
            "source_name": "shodan",
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
