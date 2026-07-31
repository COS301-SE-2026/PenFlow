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
        fingerprint_block = fingerprint_results.get("fingerprint", {})
        software_list = fingerprint_block.get("software", [])
        technologies = []

        for software_entry in software_list:
            confidence_label = software_entry.get("confidence", "low")

            confidence_map = {
                "low": 0.40,
                "medium": 0.70,
                "high": 0.95,
            }

            technologies.append(
                {
                    "technology_type": software_entry.get("category", "unknown"),
                    "product": software_entry.get("product", "unknown"),
                    "version": software_entry.get("version"),
                    "confidence": confidence_map.get(
                        confidence_label,
                        0.40,
                    ),
                    "detection_source": "fingerprint",
                    "evidence": {
                        "vendor": software_entry.get("vendor"),
                        "evidence_source": software_entry.get(
                            "evidence_score",
                            0,
                        ),
                        "sources": software_entry.get("sources", []),
                        "confidence_label": confidence_label,
                        "target_url": target_url,
                    },
                }
            )

        # package successful worker results
        result = {
            "scan_id": scan_id,
            "source_name": "fingerprint",
            "status": "completed",
            "raw_result": fingerprint_results,
            "assets": [],
            "services": [],
            "technologies": technologies,
            "findings": [],
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
            "assets": [],
            "services": [],
            "technologies": [],
            "findings": [],
            "error_message": str(error),
        }

    # send the results back to the orchestrator
    send_source_callback (
        scan_id=result["scan_id"],
        source_name=result["source_name"],
        status=result["status"],
        raw_result=result["raw_result"],
        assets=result["assets"],
        services=result["services"],
        technologies=result["technologies"],
        findings=result["findings"],
        error_message=result.get("error_message"),
    )

    if result["status"] == "completed":
        software_inventory = result["raw_result"].get("fingerprint", {}).get("software", [])

        celery_app.send_task(
            "scan.phase2_cpe_resolver",
            args=[scan_id, software_inventory],
        )


    return result
