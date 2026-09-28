import logging
from ipaddress import ip_address
from typing import Any

from app.queue.celery_app import celery_app
from app.services.target_resolution_service import resolve_target_scope
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
    hostnames: list[str] | None = None,
) -> JSONDict:
    """
    Resolves the live IPv4 and IPv6 addresses for a verified domain.
    """

    active_scope = hostnames or [domain]

    logger.info(
        "[Target Resolution] Starting worker for %s hostname(s) under %s",
        len(active_scope),
        domain,
    )

    try:
        send_source_callback(scan_id=scan_id, source_name="target_resolution", status="running")
    except Exception:
        logger.warning("[Target Resolution] Failed to send `running` callback for %s", scan_id)

    try:
        resolved_scope = resolve_target_scope(active_scope)

        assets = [
            {
                "identifier": address,
                "asset_type": f"ipv{ip_address(address).version}",
                "asset_metadata": {
                    "source_domain": domain,
                    "hostnames": hostname_list,
                    "ip_version": ip_address(address).version,
                    "resolution_source": "dns",
                },
            }
            for address, hostname_list in resolved_scope["ip_to_hostnames"].items()
        ]

        has_targets = bool(resolved_scope["ip_to_hostnames"])
        status = "completed" if has_targets else "failed"
        error_message = (
            None 
            if has_targets
            else "No public IPv4 or IPv6 addresses were resolved."
        )

        result = {
            "scan_id": scan_id,
            "source_name": "target_resolution",
            "status": status,
            "raw_result": resolved_scope,
            "assets": assets,
            "services": [],
            "technologies": [],
            "findings": [],
        }

        if error_message:
            result["error_message"] = error_message

    except Exception as error:
        logger.exception(
            "[Target Resolution] Worker failed while resolving the scope for %s",
            domain,
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

        targets = result["raw_result"].get("targets", [])

        celery_app.send_task(
            "scan.phase2_nmap",
            args=[scan_id, targets],
        )

    else:
        for source_name in (
            "nmap",
            "http_security",
            "tls",
            "fingerprint",
            "cve",
        ):
            send_source_callback(
                scan_id=scan_id,
                source_name=source_name,
                status="skipped",
                raw_result={
                    "reason": "No public scan targets were resolved.",
                },
            )

    return result
