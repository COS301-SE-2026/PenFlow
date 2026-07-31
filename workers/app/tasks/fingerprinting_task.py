import logging
from typing import Any, Optional

from app.queue.celery_app import celery_app
from app.services.fingerprinting_service import FingerprintingService
from app.utils.callback import send_source_callback

logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]


@celery_app.task(
    name="scan.phase2_fingerprint",
    bind=True,
    max_retries=2,
)
def run_fingerprinting_scan_task(
    self: Any,
    scan_id: str,
    target_url: str,
    nmap_data: Optional[dict[str, Any]] = None,
    tls_data: Optional[dict[str, Any]] = None,
) -> JSONDict:

    logger.info(f"[Fingerprint_Task] Starting fingerprint scan for {target_url}")

    try:
        send_source_callback(scan_id=scan_id, source_name="fingerprint", status="running")
    except Exception:
        logger.warning("[Fingerprint_Task] Failed to send `running` callback for %s",target_url)

    try:
        # run the fingerprinting service
        fingerprinting_service = FingerprintingService(
            target_url=target_url,
            nmap_data=nmap_data,
            tls_data=tls_data,
        )

        fingerprint_results = fingerprinting_service.run()

        # convert discovered software into orchestrator assets
        software_assets = []
        fingerprint_block = fingerprint_results.get("fingerprint", {})
        software_list = fingerprint_block.get("software", [])

        for software_entry in software_list:
            # if we dont have the signature its unknown
            product_name = software_entry.get(
                "product",
                "unknown",
            )

            asset = {
                "type": "software",
                "value": product_name,
                "metadata": software_entry,
            }

            software_assets.append(asset)

        # package successful worker results
        result = {
            "scan_id": scan_id,
            "source_name": "fingerprint",
            "status": "completed",
            "raw_result": fingerprint_results,
            "findings": [],
            "assets": software_assets,
        }

    except Exception as error:
        logger.exception(f"[Fingerprint_Task] Failed: {error}")

        # package failed worker results
        result = {
            "scan_id": scan_id,
            "source_name": "fingerprint",
            "status": "failed",
            "raw_result": {
                "target": target_url,
                "error": str(error),
            },
            "findings": [],
            "assets": [],
            "error_message": str(error),
        }

    # send the results back to the orchestrator
    send_source_callback(
        scan_id=result["scan_id"],
        source_name=result["source_name"],
        status=result["status"],
        raw_result=result["raw_result"],
        findings=result["findings"],
        assets=result["assets"],
        error_message=result.get("error_message"),
    )

    if result["status"] == "completed":
        software_inventory = result["raw_result"].get("fingerprint", {}).get("software", [])

        celery_app.send_task(
            "scan.phase2_cpe_resolver",
            args=[scan_id, software_inventory],
        )

    return result
