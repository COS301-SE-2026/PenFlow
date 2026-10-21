from typing import Any

from app.queue.celery_app import celery_app
from app.utils.callback import send_scan_callback
from app.utils.phase2_authorisation import require_phase2_authorisation

JSONDict = dict[str, Any]


@celery_app.task(name="scan.full")
def run_full_scan(scan_id: str, domain: str) -> JSONDict:
    tasks = [
        "scan.dns",
        "scan.urlscan",
        "scan.wappalyzer",
        "scan.crt_sh",
        "scan.shodan",
        "scan.hibp",
    ]

    for task in tasks:
        celery_app.send_task(task, args=[scan_id, domain])

    return {
        "scan_id": scan_id,
        "scan_type": "passive_ctem",
        "status": "queued",
    }


@celery_app.task(name="scan.phase2_full")
def run_phase2_full_scan(scan_id: str, domain: str) -> JSONDict:

    try:
        permission = require_phase2_authorisation(
            scan_id,
            stage="bootstrap",
            domain=domain,
        )
        domain = permission["domain"]

    except Exception:
        send_scan_callback(
            scan_id,
            "failed",
            "Phase 2 authorisation check failed",
        )
        raise

    tasks = [
        "scan.dns",
        "scan.shodan",
        "scan.hibp",
    ]

    for task in tasks:
        celery_app.send_task(task, args=[scan_id, domain])

    celery_app.send_task(
        "scan.crt_sh",
        args=[scan_id, domain, True],
    )

    return {
        "scan_id": scan_id,
        "scan_type": "active_vulnerability",
        "status": "queued",
    }
