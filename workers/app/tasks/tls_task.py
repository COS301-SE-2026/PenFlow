import logging
from typing import Any

from app.queue.celery_app import celery_app
from app.services.tls_service import run_tls_scan
from app.utils.callback import send_source_callback

logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]


@celery_app.task(
    name="scan.phase2_tls",
    bind=True,
    max_retries=2,
)
def run_tls_scan_task(
    self: Any,
    scan_id: str,
    ip_address: str,
    ports: list[JSONDict],
    hostname: str | None = None,
) -> JSONDict:
    """
    Does tls inspection off of the valid ports provided by nmap
    """

    logger.info(f"[TLS_Task] Starting TLS scan for IP address: {ip_address}")

    try:
        tls_data = run_tls_scan(
            ip_address=ip_address,
            ports=ports,
            hostname=hostname,
        )

        findings: list[JSONDict] = []
        assets: list[JSONDict] = []

        for target in tls_data["targets"]:
            # handshake fails
            if "error" in target:
                findings.append(
                    {
                        "title": "TLS Handshake Failed",
                        "description": target["error"],
                        "severity": "low",
                        "target": f"{ip_address}:{target['port']}",
                    }
                )

                continue

            certificate = target["certificate"]
            # assets
            assets.append(
                {
                    "type": "tls_certificate",
                    "value": f"{ip_address}:{target['port']}",
                    "metadata": {
                        "subject": certificate["subject"],
                        "issuer": certificate["issuer"],
                        "valid_from": certificate["valid_from"],
                        "valid_until": certificate["valid_until"],
                        "tls_version": target["tls_version"],
                        "cipher": target["cipher"],
                    },
                }
            )

            # Findings
            if certificate["expired"]:
                findings.append(
                    {
                        "title": "Expired TLS Certificate",
                        "description": "The TLS certificate has expired.",
                        "severity": "high",
                        "target": f"{ip_address}:{target['port']}",
                    }
                )

        # valid results + assets and findings determined above
        result = {
            "scan_id": scan_id,
            "source_name": "tls",
            "status": "completed",
            "raw_result": tls_data,
            "findings": findings,
            "assets": assets,
        }

    except Exception as error:
        logger.exception(f"[TLS_Task] Failed while scanning {ip_address}: {error}")

        # errored results
        result = {
            "scan_id": scan_id,
            "source_name": "tls",
            "status": "failed",
            "raw_result": {
                "ip": ip_address,
                "error": str(error),
            },
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
