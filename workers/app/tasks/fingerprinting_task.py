import logging
from typing import Any, Optional

from app.queue.celery_app import celery_app
from app.utils.job_runner import dispatch_scan_job 
from app.utils.db_utils import get_ports_from_db, get_technologies_from_db 

logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]


@celery_app.task(
    name="scan.phase2_fingerprint",
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,), retry_backoff=True
)
def run_fingerprinting_scan_task(
    self: Any,
    scan_id: str,
    target_url: str,
    nmap_data: Optional[dict[str, Any]] = None,
    tls_data: Optional[dict[str, Any]] = None
) -> JSONDict:

    db_ports = get_ports_from_db(scan_id)
    hydrated_nmap_data = {"ports": db_ports} if db_ports else {}

    payload = {"scan_id": scan_id, "target_url": target_url, "nmap_data": hydrated_nmap_data, "tls_data": tls_data or {}}
    success = dispatch_scan_job("fingerprint", payload)

    if not success:
        raise RuntimeError(f"Fargate/Docker container failed for Fingerprint scan {scan_id}")

    inventory = get_technologies_from_db(scan_id)
    celery_app.send_task("scan.phase2_cpe_resolver", args=[scan_id, inventory])

    return {"status": "completed", "scan_id": scan_id, "source_name": "fingerprints"}