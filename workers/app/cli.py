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

