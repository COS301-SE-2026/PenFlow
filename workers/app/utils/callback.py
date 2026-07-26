import logging
import os

import httpx

logger = logging.getLogger(__name__)
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:3001/api/v1")


def send_scan_callback(scan_id: str, status: str, error_message: str | None = None) -> None:
    url = f"{BACKEND_API_URL}/internal/scans/{scan_id}/status"
    payload = {
        "status": status,
        "error_message": error_message,
    }

    try:
        with httpx.Client(timeout=30) as client:
            response = client.patch(url, json=payload)
            response.raise_for_status()
    except Exception:
        logger.exception("Failed to send scan callback for %s", scan_id)
        raise


def send_report_callback(
    scan_id: str, status: str, pdf_path: str | None = None, error_message: str | None = None
) -> None:
    url = f"{BACKEND_API_URL}/internal/reports/{scan_id}/status"
    payload = {
        "status": status,
        "pdf_path": pdf_path,
        "error_message": error_message,
    }

    try:
        with httpx.Client(timeout=30) as client:
            response = client.patch(url, json=payload)
            response.raise_for_status()
    except Exception:
        logger.exception("Failed to send report callback for %s", scan_id)


def send_source_callback(
    scan_id: str,
    source_name: str,
    status: str,
    raw_result: dict | None = None,
    findings: list[dict] | None = None,
    assets: list[dict] | None = None,
    error_message: str | None = None,
) -> None:
    url = f"{BACKEND_API_URL}/internal/scans/{scan_id}/sources/{source_name}"

    payload = {
        "status": status,
        "raw_result": raw_result,
        "findings": findings or [],
        "assets": assets or [],
        "error_message": error_message,
    }

    try:
        with httpx.Client(timeout=30) as client:
            response = client.patch(url, json=payload)
            response.raise_for_status()

    except Exception:
        logger.exception(
            "Failed to send the source callback for scan %s source %s",
            scan_id,
            source_name,
        )
        raise
