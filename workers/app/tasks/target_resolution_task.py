import logging
from typing import Any

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
    self: Any,
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
        assets = [
                     {
                         "identifier": ip,
                         "asset_type": "ipv4",
                         "asset_metadata": {
                             "source_domain": domain,
                         }
                     }
                     for ip in ip_data["ipv4"]
                 ] + [
                     {
                         "identifier": ip,
                         "asset_type": "ipv6",
                         "asset_metadata": {
                             "source_domain": domain,
                         }
                     }
                     for ip in ip_data["ipv6"]
                 ]

        has_targets = bool(
            ip_data["ipv4"] or ip_data["ipv6"]
        )

        status = "completed" if has_targets else "failed"

        error_message = (
            None
            if has_targets
            else "No IPv4 or IPv6 addresses were resolved."
        )

        result = {
            "scan_id": scan_id,
            "source_name": "target_resolution",
            "status": status,
            "raw_result": ip_data,
            "assets": assets,
            "services": [],
            "technologies": [],
            "findings": [],
        }

        if error_message:
            result["error_message"] = error_message

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
            "assets": [],
            "services": [],
            "technologies": [],
            "findings": [],
            "error_message": str(error),
        }

    send_source_callback(
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
        ipv4_addresses = result["raw_result"].get("ipv4", [])
        ipv6_addresses = result["raw_result"].get("ipv6", [])

        for ip_address in ipv4_addresses + ipv6_addresses:
            celery_app.send_task(
                "scan.phase2_nmap",
                args=[scan_id, ip_address, domain],
            )

    return result