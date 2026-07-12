from typing import Any

from app.queue.celery_app import celery_app
from app.utils.callback import send_scan_callback

JSONDict = dict[str, Any]


@celery_app.task(name="scan.full")
def run_full_scan(scan_id: str, domain: str) -> JSONDict:
    tasks = [
        "scan.dns",
        "scan.urlscan",
        "scan.wappalyzer",
        "scan.crt_sh",
        "scan.shodan",
        "scan.hunter",
        "scan.hibp",
    ]

    for task in tasks:
        celery_app.send_task(task, args=[scan_id, domain])

    return {
        "scan_id": scan_id,
        "status": "queued",
    }