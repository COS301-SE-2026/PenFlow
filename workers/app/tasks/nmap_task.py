import logging
from typing import Any

from app.queue.celery_app import celery_app
from app.services.nmap_service import run_live_nmap_scan
from app.utils.callback import send_source_callback

logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]


@celery_app.task\
(
    name="scan.phase2_nmap",
    bind=True,
    max_retries=2,
)
def run_nmap_scan\
(
    self: Any,
    scan_id: str,
    ip_address: str,
    domain: str,
    profile: str = "standard",
) -> JSONDict:
    """
    Executes nmap Scan on a single ip address provided by the target resolution worker

    We have the ability to run multiple scans simultaneously in the occurence of many ip's
    """

    (logger.info
    (
        f"[NMAP_Task] Starting '{profile}' scan for IP: {ip_address}"
    ))

    try:
        scan_data = (run_live_nmap_scan
        (
            ip_address=ip_address,
            profile=profile,
        ))

        services = []

        for port in scan_data.get("ports", []):
            services.append(
                {
                    "host": scan_data["ip"],
                    "port": port["port"],
                    "protocol": port["protocol"],
                    "service_name": port["service"],
                    "product": port["product"],
                    "version": port["version"],
                    "banner": port.get("extra_info"),
                    "state": port["state"],
                    "tls_enabled": False,
                }
            )

        result = {
            "scan_id": scan_id,
            "source_name": "nmap",
            "status": "completed",
            "raw_result": scan_data,
            "assets": [],
            "services": services,
            "technologies": [],
            "findings": [],
            
        }

        (logger.info
        (
            f"[NMAP_Task] Completed scan for {ip_address}. "
            f"Discovered {len(scan_data.get('ports', []))} open services."
        ))

    except Exception as error:
        (logger.exception
        (
            f"[NMAP_Task] Failed while scanning {ip_address}: {error}"
        ))

        result = {
            "scan_id": scan_id,
            "source_name": "nmap",
            "status": "failed",
            "raw_result":
            {
                "profile": profile,
                "ip": ip_address,
                "error": str(error),
            },
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
        ports = result["raw_result"].get("ports", [])

        celery_app.send_task(
            "scan.phase2_tls",
            args=[scan_id, ip_address, ports, domain],
        )

        celery_app.send_task(
            "scan.phase2_http_security",
            args=[scan_id, domain, ip_address, ports],
        )

        celery_app.send_task(
            "scan.phase2_fingerprint",
            args=[scan_id, f"https://{domain}", result["raw_result"], None]
        )

    return result