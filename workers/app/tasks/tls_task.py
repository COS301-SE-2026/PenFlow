import logging
from typing import Any

from app.queue.celery_app import celery_app
from app.services.tls_service import run_tls_scan
from app.utils.callback import send_source_callback

logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]

@celery_app.task\
(
    name="scan.phase2_tls",
    bind=True,
    max_retries=2,
)
def run_tls_scan_task\
(
    self: Any,
    scan_id: str,
    ip_address: str,
    ports: list[JSONDict],
    hostname: str | None = None,
) -> JSONDict:
    """
    Does tls inspection off of the valid ports provided by nmap
    """

    logger.info(
        f"[TLS_Task] Starting TLS scan for IP address: {ip_address}"
    )

    try:

        tls_data = run_tls_scan(
            ip_address=ip_address,
            ports=ports,
            hostname=hostname,
        )

        findings: list[JSONDict] = []

        for target in tls_data["targets"]:

            #handshake fails
            if "error" in target:

                findings.append(
                    {
                        "source": "tls",
                        "title": "TLS Handshake Failed",
                        "description": target["error"],
                        "recommendation": (
                            "Review the TLS configuration for this service and ensure "
                            "the endpoint supports a valid TLS handshake."
                        ),
                        "severity": "low",
                        "host": ip_address,
                        "port": target["port"],
                        "protocol": "tcp",
                        "evidence": {
                            "error": target["error"],
                        },
                    }
                )

                continue

            certificate = target["certificate"]

            #Findings
            if certificate["expired"]:

                findings.append\
                (
                    {
                        "source": "tls",
                        "title": "Expired TLS Certificate",
                        "description": "The TLS certificate has expired.",
                        "recommendation": (
                            "Renew or replace the TLS certificate with a valid certificate."
                        ),
                        "severity": "high",
                        "host": ip_address,
                        "port": target["port"],
                        "protocol": "tcp",
                        "evidence": {
                            "subject": certificate["subject"],
                            "issuer": certificate["issuer"],
                            "valid_from": certificate["valid_from"],
                            "valid_until": certificate["valid_until"],
                            "tls_version": target["tls_version"],
                            "cipher": target["cipher"],
                        },
                    }
                )

            if certificate["self_signed"]:
                findings.append(
                    {
                        "source": "tls",
                        "title": "Self-Signed TLS Certificate",
                        "description": "The TLS endpoint is using a self-signed certificate.",
                        "recommendation": (
                            "Use a certificate issued by a trusted certificate authority "
                            "for publicly exposed services."
                        ),
                        "severity": "medium",
                        "host": ip_address,
                        "port": target["port"],
                        "protocol": "tcp",
                        "evidence": {
                            "subject": certificate["subject"],
                            "issuer": certificate["issuer"],
                        },
                    }
                )

        #valid results + assets and findings determined above
        result = \
        {
            "scan_id": scan_id,
            "source_name": "tls",
            "status": "completed",
            "raw_result": tls_data,
            "assets": [],
            "services": [],
            "technologies": [],
            "findings": findings,
        }

    except Exception as error:

        logger.exception\
        (
            f"[TLS_Task] Failed while scanning "
            f"{ip_address}: {error}"
        )

        #errored results
        result = \
        {
            "scan_id": scan_id,
            "source_name": "tls",
            "status": "failed",
            "raw_result":
            {
                "ip": ip_address,
                "error": str(error),
            },
            "assets": [],
            "services": [],
            "technologies": [],
            "findings": [],
            "error_message": str(error),
        }

    send_source_callback\
    (
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

    return result