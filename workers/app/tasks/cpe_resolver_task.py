import logging
from typing import Any

from app.queue.celery_app import celery_app
from app.services.cpe_resolver_service import run_cpe_resolution
from app.utils.callback import send_source_callback

logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]


@celery_app.task(
    name="scan.phase2_cpe_resolver",
    bind=True,
    max_retries=2,
)
def run_cpe_resolver_task(
    self: Any,
    scan_id: str,
    software_inventory: list[JSONDict],
) -> JSONDict:

    logger.info(
        f"[CPE_Task] Starting CPE resolution for: {len(software_inventory)} objects.",
        len(software_inventory),
    )

    resolved_data: list[JSONDict] = []
    
    try:
        resolved_data = run_cpe_resolution(software_inventory)

        technologies = []

        for software in resolved_data:
            evidence_score = software.get("evidence_score", 0)

            technologies.append(
                {
                    "technology_type": software.get(
                        "category",
                        "software",
                    ),
                    "product": software.get(
                        "product",
                        "unknown",
                    ),
                    "version": software.get("version"),
                    "confidence": evidence_score / 100,
                    "detection_source": "cpe_resolver",
                    "host": software.get("host"),
                    "port": software.get("port"),
                    "protocol": software.get("protocol"),
                    "evidence": {
                        **software,
                        "cpe": software.get("cpe"),
                    },
                }
            )

        result = {
            "scan_id": scan_id,
            "source_name": "cpe_resolver",
            "status": "completed",
            "raw_result": {
                "resolved_inventory": resolved_data,
            },
            "assets": [],
            "services": [],
            "technologies": technologies,
            "findings": [],
        }

    except Exception as error:
        logger.exception(f"[CPE_Task] Failed: {error}")

        result = {
            "scan_id": scan_id,
            "source_name": "cpe_resolver",
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

    if result["status"] == "completed":

        celery_app.send_task(
            "scan.phase2_cve",
            args=[scan_id, resolved_data],
        )


    return result
