from typing import Any
import logging
from app.queue.celery_app import celery_app
from app.services.target_resolution_service import resolve_target_ips
from app.utils.callback import send_source_callback
logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]


@celery_app.task(
    name="scan.phase2_target_resolution",
    bind=True,
    max_retries=3,
)

def run_target_resolution(
    self,
    scan_id: str,
    domain: str,
) -> JSONDict:
    """
    Resolves the live IPv4 and IPv6 addresses for a verified domain.
    """

    logger.info(
        f"[Target Resolution] Starting worker for the domain: {domain}"
    )

    try:
        ip_data = resolve_target_ips(domain)
        assets = (
            [
                {
                    "type": "ipv4",
                    "value": ip,
                }
                for ip in ip_data["ipv4"]
            ]
            + [
                {
                    "type": "ipv6",
                    "value": ip,
                }
                for ip in ip_data["ipv6"]
            ]
        )

        result = {
            "scan_id": scan_id,
            "source_name": "target_resolution",
            "status": "completed",
            "raw_result": ip_data,
            #findings and assets are both blank we just want the ip's
            "findings": [],
            "assets": assets,
        }

    except Exception as error:
        logger.exception(
            f"[Target Resolution] Worker failed while resolving the domain: {domain}"
        )

        result = {
            "scan_id": scan_id,
            "source_name": "target_resolution",
            "status": "failed",
            "raw_result": {
                "error": str(error),
            },
            # findings and assets are both blank we just want the ip's
            "findings": [],
            "assets": [],
            "error_message": str(error),
        }

    send_source_callback(
        scan_id=result["scan_id"],
        source_name=result["source_name"],
        status=result["status"],
        raw_result=result["raw_result"],
        findings=result["findings"],
        assets=result["assets"],
        error_message=result.get("error_message"),
    )

    return result