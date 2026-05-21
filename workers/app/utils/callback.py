import logging
import os

import httpx

logger = logging.getLogger(__name__)
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:3001/api/v1")


def send_scan_callback(
    scan_id: str, status: str, results: dict | None = None, error_message: str | None = None
) -> None:
    url = f"{BACKEND_API_URL}/internal/scans/{scan_id}/status"
    payload = {
        "status": status,
        "results": results,
        "error_message": error_message,
    }

    try:
        with httpx.Client(timeout=30) as client:
            client.patch(url, json=payload)
    except Exception:
        logger.exception("Failed to send scan callback for %s", scan_id)


def send_report_callback(
    scan_id: str, status: str, pdf_path: str | None = None, error_message: str | None = None
) -> None:
    url = f"{BACKEND_API_URL}/internal/reports/{scan_id}/status"
    payload = {
        "status": status,
        "pdf_path": pdf_path,
        "error_message": error_message,
    }

    with httpx.Client(timeout=30) as client:
        client.patch(url, json=payload)