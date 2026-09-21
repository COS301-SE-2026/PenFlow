import logging
from typing import Any

from app.queue.celery_app import celery_app
from app.utils.job_runner import dispatch_scan_job 
from app.utils.db_utils import get_ports_from_db 
from app.utils.callback import send_source_callback

logger = logging.getLogger(__name__)

@celery_app.task(
    name="scan.phase2_tls",
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,), 
    retry_backoff=True
)
def run_tls_scan_task(
    self: Any,
    scan_id: str,
    ip_address: str,
    ports: list[Any],
    domain: str = None
) -> dict[str, Any]:
    """
    Does tls inspection off of the valid ports provided by nmap
    """

    db_ports = get_ports_from_db(scan_id)
    if not db_ports: 
        logger.info(f"No ports found for {scan_id}. Skipping TLS scan.")
        send_source_callback(scan_id=scan_id, source_name="tls", status="skipped")
        return {"status": "skipped", "scan_id": scan_id, "source_name": "tls"}

    payload = {"scan_id": scan_id, "ip_address": ip_address, "ports": db_ports, "hostname": domain}
    success = dispatch_scan_job("tls", payload)

    if not success: 
        raise RuntimeError(f"Fargate/Docker conainer failed for TLS scan {scan_id}")

    return {"status": "completed", "scan_id": scan_id, "source_name": "tls"}