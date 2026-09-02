import logging 
import os 
import time
from typing import Any 

import httpx 

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3001")

logger = logging.getLogger(__name__) 

def send_scan_callback(
        scan_id: str, 
        status: str, 
        error_message: str | None = None
) -> dict[str, Any] | None: 
    """
    Updates main scan status in the backend.
    """
    payload = {"status": status, "error_message": error_message} 
    url = f"{API_BASE_URL}/api/v1/internal/scans/{scan_id}/status" 

    try: 
        response = httpx.patch(url, json=payload, timeout=10.0)
        response.raise_for_status() 
        return response.json() 
    except Exception as error: 
        logger.error("Failed to send scan callback for %s: %s", scan_id, error)
        return None 

def send_source_callback(
        scan_id: str, 
        source_name: str, 
        payload: dict[str, Any]
) -> dict[str, Any] | None: 
    """ 
    Updates the status of a specific scan source/tool. 
    """

    url = f"{API_BASE_URL}/api/v1/internal/scans/{scan_id}/sources/{source_name}"

    try: 
        response = httpx.patch(url, json=payload, timeout=10.0) 
        response.raise_for_status() 
        return response.json() 
    except Exception as error: 
        logger.error("Failed to send source callback for %s source %s: %s", scan_id, source_name, error)
        return None 

def send_report_callback(
        scan_id: str,
        status: str, 
        pdf_path: str | None = None, 
        error_message: str | None = None,
) -> dict[str, Any] | None:
    """
    Sends a callback to the API indicating that a scan report generation
    (Phase 1/2) has completed or failed.
    """
    payload = {
        "status": status, 
        "pdf_path": pdf_path, 
        "error_message": error_message,
    }

    url = f"{API_BASE_URL}/api/v1/internal/reports/{scan_id}/status"
    try:
        response = httpx.patch(url, json=payload, timeout=10.0)
        response.raise_for_status()
        return response.json() 
    except Exception as error: 
        logger.error("Failed to send scan report callback for %s: %s", scan_id, error)
        return None 

def send_engagement_report_callback(
        engagement_id: str,
        version: int, 
        status: str, 
        pdf_path: str | None = None, 
        error_message: str | None = None,
        max_retries: int = 3,
) ->dict[str, Any] | None:
    """
    Sends a callback to the API indicating that a Phase 3  manualengagement 
    report generation has completed or failed. 
    """
    payload = {
        "status": status, 
        "pdf_path": pdf_path, 
        "error_message": error_message,
    }

    url = f"{API_BASE_URL}/api/v1/internal/reports/engagement/{engagement_id}/version/{version}/callback"


    for attempt in range(1, max_retries + 1):
        try:
            response = httpx.put(url, json=payload, timeout=10.0)
            response.raise_for_status() 
            return response.json()
        except httpx.HTTPError as error: 
            logger.warning(f"Callback attempt {attempt} failed: {error}")
            if attempt == max_retries: 
                return None
            time.sleep(2 ** attempt)