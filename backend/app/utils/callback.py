import logging 
from typing import Any 

import httpx 

from app.core.config import settings 

logger = logging.getLogger(__name__) 

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

    url = f"{settings.API_BASE_URL}/api/v1/reports/scan/{scan_id}/callback" 

    try:
        response = httpx.put(url, json=payload, timeout=10.0)
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

    url = f"{settings.API_BASE_URL}/api/v1/reports/engagement/{engagement_id}/version/{version}/callback"

    try:
        response = httpx.put(url, json=payload, timeout=10.0)
        response.raise_for_status() 
        return response.json()
    except Exception as error: 
        logger.error(
            "Failed to send engagement report callback for %s (v%s): %s", 
            engagement_id, version, error
        )
        return None