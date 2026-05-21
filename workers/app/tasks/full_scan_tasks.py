from typing import Any
from celery import chord
from app.queue.celery_app import celery_app
from app.utils.callback import send_scan_callback

JSONDict = dict[str, Any]


@celery_app.task(name="scan.aggregate")
def aggregate_scan_results(results: list[JSONDict], scan_id: str) -> JSONDict:
    failed_sources = [
        item.get("source_name")
        for item in results
        if item.get("status") != "completed"
    ]

    status = "completed" if len(failed_sources) < len(results) else "failed"
    payload = {
        "scan_id": scan_id,
        "status": status,
        "results": {
            "subtasks": results,
            "failed_sources": failed_sources,
        },
    }

    send_scan_callback(
        scan_id,
        status,
        results=payload["results"],
    )

    return payload


@celery_app.task(name="scan.full")
def run_full_scan(scan_id: str, domain: str) -> JSONDict:
    workflow = chord(
        [
            celery_app.signature("scan.dns", args=[scan_id, domain]),
            celery_app.signature("scan.urlscan", args=[scan_id, domain]),
            celery_app.signature("scan.wappalyzer", args=[scan_id, domain]),
            celery_app.signature("scan.crt_sh", args=[scan_id, domain]),
            celery_app.signature("scan.shodan", args=[scan_id, domain]),
            celery_app.signature("scan.hunter", args=[scan_id, domain]),
            celery_app.signature("scan.hibp", args=[scan_id, domain]),
        ]
    )(aggregate_scan_results.s(scan_id))

    return {
        "scan_id": scan_id,
        "workflow_id": workflow.id,
        "status": "queued",
    }