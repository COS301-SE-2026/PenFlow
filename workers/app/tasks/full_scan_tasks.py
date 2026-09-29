from typing import Any

from app.queue.celery_app import celery_app

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
