import logging
from typing import Any

from app.queue.celery_app import celery_app
from app.services.cve_service import run_cve_scan
from app.utils.callback import send_source_callback

logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]

@celery_app.task\
(
    name="scan.phase2_cve",
    bind=True,
    max_retries=2,
)

def run_cve_scan_task\
(
    self: Any,
    scan_id: str,
    resolved_inventory: list[JSONDict],
) -> JSONDict:
    """
    Task to facilitate cve scan, should take fingerprint tech stack as well,
    as the cpe credentials resolved.

    Query NVD and return vulnerabilities
    """
    logger.info(
        f"[CVE_Task] Starting correlation for: {len(resolved_inventory)} resolved components."
    )

    try:
        vulnerabilities = run_cve_scan(resolved_inventory)
        findings = []
        for vulnerability in vulnerabilities:
            findings.append\
            (
                {
                    "severity": vulnerability.get("severity", "medium"),
                    "title":
                    (
                        f"{vulnerability.get('cve_id')} detected in "
                        f"{vulnerability.get('affected_software')}"
                    ),
                    "description":
                    (
                        vulnerability.get(
                            "description",
                            "No description provided.",
                        )
                    ),
                    "remediation":
                    (
                        vulnerability.get(
                            "remediation",
                            "Update to the latest patched version.",
                        )
                    ),
                    "target":
                    (
                        vulnerability.get("affected_software")
                    ),
                    "metadata":
                    {
                        "cve_id":
                        (
                            vulnerability.get("cve_id")
                        ),
                        "cvss_score":
                        (
                            vulnerability.get("cvss_score")
                        ),
                    },
                }
            )

        result = \
        {
            "scan_id": scan_id,
            "source_name": "cve",
            "status": "completed",
            "raw_result":
            {
                "vulnerabilities": vulnerabilities,
            },
            "findings": findings,
            "assets": [],
        }

    except Exception as error:
        logger.exception\
        (
            f"[CVE_Task] Pipeline failed: {error}"
        )

        result = \
        {
            "scan_id": scan_id,
            "source_name": "cve",
            "status": "failed",
            "raw_result":
            {
                "error": str(error),
            },
            "findings": [],
            "assets": [],
            "error_message": str(error),
        }

    send_source_callback\
    (
        scan_id=result["scan_id"],
        source_name=result["source_name"],
        status=result["status"],
        raw_result=result["raw_result"],
        findings=result["findings"],
        assets=result["assets"],
        error_message=result.get("error_message"),
    )

    return result