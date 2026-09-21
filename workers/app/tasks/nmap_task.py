import logging
from typing import Any

from app.queue.celery_app import celery_app
from app.utils.job_runner import dispatch_scan_job 

logger = logging.getLogger(__name__)

@celery_app.task(
    name="scan.phase2_nmap",
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def run_nmap_scan(
    self: Any,
    scan_id: str,
    ip_address: str,
    domain: str,
    profile: str = "standard",
) -> dict[str, Any]:
    """
    Executes nmap Scan on a single ip address provided by the target resolution worker

    We have the ability to run multiple scans simultaneously in the occurence of many ip's
    """

    (logger.info(f"[NMAP_Task] Dispatching isolated job for IP: {ip_address}"))
    payload = {"scan_id": scan_id, "ip_address": ip_address, "domain": domain, "profile": profile}

    success = dispatch_scan_job("nmap", payload)

    if not success:
        raise RuntimeError(f"Fargate/Docker container failed for NMAP scan {scan_id}")

    celery_app.send_task("scan.phase2_tls", args=[scan_id, ip_address, domain])
    celery_app.send_task("scan.phase2_http_security", args=[scan_id, domain, ip_address])
    celery_app.send_task("scan.phase2_fingerprint", args=[scan_id, f"https://{domain}", {}, None])

    return{"status": "completed", "scan_id": scan_id, "source_name": "nmap"}