import sys 
import argparse 
import json 
import logging 
from typing import Any 

from app.services.nmap_service import run_live_nmap_scan 
from app.services.tls_service import run_tls_scan 
from app.services.http_security_service import run_http_security_scan 
from app.services.fingerprinting_service import FingerprintingService 
from app.utils.callback import send_source_callback 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def safe_failure_callback(scan_id: str, source_name: str, error: Exception) -> None: 
    try: 
        send_source_callback(
            scan_id=scan_id,
            source_name=source_name, 
            status="failed", 
            raw_result={"error": str(error)}, 
            error_message=str(error)
        )
    except Exception as cb_e: 
        logger.error(f"Failed to send failures callback for {source_name}: {cb_e}")

def handle_nmap(payload: dict[str, Any]) -> None: 
    scan_id = payload["scan_id"]
    try:
        send_source_callback(scan_id=scan_id, source_name="nmap", status="running")
        scan_data = run_live_nmap_scan(ip_address=payload["ip_address"], profile=payload.get("profile", "standard"))

        services = [
            {
                "host": scan_data["ip"], "port": p["port"], "protocol": p["protocol"],
                "service_name": p["service"], "product": p["product"], "version": p["version"], 
                "banner": p.get("extra_info"), "state": p["state"], "tls_enabled": False,
            } for p in scan_data.get("ports", [])
        ]
        send_source_callback(scan_id=scan_id, source_name="nmap", status="completed", raw_result=scan_data, services=services)
    except Exception as error:
        logger.exception(f"NMAP failed: {error}")
        safe_failure_callback(scan_id, "nmap", error)
        raise 