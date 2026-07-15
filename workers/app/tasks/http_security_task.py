from typing import Any
import logging
from app.queue.celery_app import celery_app
from app.services.http_security_service import run_http_security_scan
from app.utils.callback import send_source_callback

logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]


@celery_app.task\
(
    name="scan.phase2_http_security",
    bind=True,
    max_retries=2,
)
def run_http_security_scan\
(
    self,
    scan_id: str,
    ip_address: str,
    ports: list[JSONDict],
) -> JSONDict:
    """

    Does HTTP security check on the services/ports that nmap uncovered

    Returns:
    HTTP status
    Response headers
    Security header values

    Task generates findings for missing headers
    """

    (logger.info
    (
        f"[HTTP_Task] Starting HTTP security scan for the ip address: {ip_address}"
    ))

    try:

        scan_data = (run_http_security_scan
        (
            ip_address=ip_address,
            ports=ports,
        ))

        findings = []

        for target in scan_data.get("targets", []):

            headers = target.get\
            (
                "security_headers",
                {},
            )

            checks = \
            {
                "Strict-Transport-Security":
                    headers.get\
                    (
                        "strict_transport_security",
                    ),

                "Content-Security-Policy":
                    headers.get\
                    (
                        "content_security_policy"
                    ),

                "X-Frame-Options":
                    headers.get\
                    (
                        "x_frame_options"
                    ),

                "Referrer-Policy":
                    headers.get\
                    (
                        "referrer_policy"
                    ),

                "Permissions-Policy":
                    headers.get\
                    (
                        "permissions_policy"
                    ),

                "X-Content-Type-Options":
                    headers.get\
                    (
                        "x_content_type_options"
                    ),
            }

            for header_name, value in checks.items():

                if value:
                    continue

                (findings.append
                (
                    {
                        #if we have no header for now we will default to a low severity
                        "severity": "low",
                        "title": f"Missing {header_name}",
                        "description":
                        (
                            f"{header_name} header is not present."
                        ),
                        "target": target["url"],
                    }
                ))

        result = \
        {
            "scan_id": scan_id,
            "source_name": "http_security",
            "status": "completed",
            "raw_result": scan_data,
            "findings": findings,
            "assets": [],
        }

        (logger.info
        (
            f"[HTTP_Task] Completed HTTP security scan for {ip_address}. "
            f"Generated {len(findings)} finding(s)."
        ))

    except Exception as error:

        (logger.exception
        (
            f"[HTTP_Task] Failed while scanning {ip_address}: {error}"
        ))

        result = \
        {
            "scan_id": scan_id,
            "source_name": "http_security",
            "status": "failed",
            "raw_result":
            {
                "ip": ip_address,
                "error": str(error),
            },
            "findings": [],
            "assets": [],
            "error_message": str(error),
        }

    (send_source_callback
    (
        scan_id=result["scan_id"],
        source_name=result["source_name"],
        status=result["status"],
        raw_result=result["raw_result"],
        findings=result["findings"],
        assets=result["assets"],
        error_message=result.get("error_message"),
    ))

    return result