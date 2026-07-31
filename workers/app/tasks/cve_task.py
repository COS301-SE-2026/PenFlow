import logging
from typing import Any

from app.queue.celery_app import celery_app
from app.services.cve_service import run_cve_scan
from app.utils.callback import send_source_callback

logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]


@celery_app.task(
    name="scan.phase2_cve",
    bind=True,
    max_retries=2,
)
def run_cve_scan_task(
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
            cve_id = vulnerability.get("cve_id")
            affected_software = vulnerability.get(
                "affected_software",
                "unknown software",
            )

            findings.append\
            (
                {
                    "source": "cve",
                    "severity": str(vulnerability.get("severity", "medium")).lower(),
                    "title":
                    (
                        f"{vulnerability.get('cve_id')} detected in "
                        f"{affected_software}"
                    ),
                    "description": (
                        vulnerability.get(
                            "description",
                            "No description provided.",
                        )
                    ),
                    "recommendation":
                    (
                        vulnerability.get(
                            "remediation",
                            "Update to the latest patched version.",
                        )
                    ),
                    "cve_id": cve_id,
                    "cvss_score": vulnerability.get("cvss_score"),
                    "host": vulnerability.get("host"),
                    "port": vulnerability.get("port"),
                    "protocol": vulnerability.get("protocol"),
                    "evidence": {
                        "cpe": vulnerability.get("cpe"),
                        "affected_software": affected_software,
                        "affected_version": vulnerability.get("affected_version"),
                    },
                }
            )

        result = {
            "scan_id": scan_id,
            "source_name": "cve",
            "status": "completed",
            "raw_result": {
                "vulnerabilities": vulnerabilities,
            },
            "assets": [],
            "services": [],
            "technologies": [],
            "findings": findings,
        }

    except Exception as error:
        logger.exception(f"[CVE_Task] Pipeline failed: {error}")

        result = {
            "scan_id": scan_id,
            "source_name": "cve",
            "status": "failed",
            "raw_result": {
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

    return result
