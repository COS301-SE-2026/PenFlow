import logging
from typing import Any

from app.queue.celery_app import celery_app
from app.utils.callback import send_source_callback
from app.utils.db_utils import get_technologies_from_db
from app.utils.job_runner import dispatch_scan_job

logger = logging.getLogger(__name__)

_PIPELINE_SOURCES = (
    "nmap",
    "http_security",
    "tls",
    "fingerprint",
)


@celery_app.task(
    name="scan.phase2_nmap",
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def run_nmap_scan(
    self: Any,
    scan_id: str,
    targets: list[dict[str, Any]],
    profile: str = "standard",
) -> dict[str, Any]:
    """
    Coordinates bounded active scanning across resolved addresses and hostnames
    """
    unique_addresses = {
        str(address)
        for target in targets
        for address in [
            *target.get("ipv4", []),
            *target.get("ipv6", []),
        ]
    }

    logger.info(
        "[NMAP_TASK] Dispatching combined active pipeline "
        "for %s unique address(es)",
        len(unique_addresses),
    )

    pipeline_succeeded = dispatch_scan_job(
        "phase2_pipeline",
        {
            "scan_id": scan_id,
            "targets": targets,
            "profile": profile,
        },
    )

    if not pipeline_succeeded:
        error_message = (
            "The isolated Phase 2 pipeline failed to start "
            "or complete."
        )

        logger.error(
            "[NMAP_TASK] %s Scan: %s",
            error_message,
            scan_id,
        )

        for source_name in _PIPELINE_SOURCES:
            send_source_callback(
                scan_id=scan_id,
                source_name=source_name,
                status="failed",
                raw_result={
                    "error": error_message,
                },
                error_message=error_message,
            )

        send_source_callback(
            scan_id=scan_id,
            source_name="cve",
            status="skipped",
            raw_result={
                "reason": (
                    "CVE matching was skipped because the "
                    "active scan pipeline did not complete."
                ),
            },
        )

        return {
            "status": "failed",
            "scan_id": scan_id,
            "source_name": "nmap",
            "unique_addresses": len(unique_addresses),
        }

    inventory = get_technologies_from_db(scan_id)
    celery_app.send_task(
        "scan.phase2_cpe_resolver",
        args=[scan_id, inventory],
    )

    return {
        "status": "completed",
        "scan_id": scan_id,
        "source_name": "nmap",
        "unique_addresses": len(unique_addresses),
    }