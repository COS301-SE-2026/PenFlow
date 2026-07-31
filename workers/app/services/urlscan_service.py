import json
import logging
import os
import time
from pathlib import Path

import httpx

# Logger to track this specific worker
logger = logging.getLogger(__name__)
DEFAULT_SCREENSHOT = "default.png"

# scan mode between live and mock
SCAN_MODE = os.getenv("SCAN_MODE", "MOCK").upper()
URLSCAN_API_KEY = os.getenv("URLSCAN_API_KEY", "fake_key_1234")

WORKERS_ROOT = Path(__file__).resolve().parent.parent.parent

SCREENSHOT_OUTPUT_DIR = Path(
    os.getenv("SCREENSHOT_OUTPUT_DIR", "/app/generated_reports/screenshots")
)


# so we can display screen shot
def _download_screenshot(image_url: str, target_filename: str) -> str:
    """Downloads an image from the web and saves it to the shared templates folder."""
    try:
        logger.info(f"Downloading live screenshot from: {image_url}")

        SCREENSHOT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        save_path = SCREENSHOT_OUTPUT_DIR / target_filename

        response = httpx.get(image_url, timeout=15.0)
        response.raise_for_status()

        # Save it directly where the PDF engine expects to find it
        with open(save_path, "wb") as f:
            f.write(response.content)

        logger.info(f"Screenshot saved successfully as: {save_path}")
        return str(save_path)
    except Exception as e:
        logger.exception(f"X Failed to download screenshot: {e}")

        # default for failure for now
        return "brocode_logo.png"


def collect_raw_data(domain: str) -> dict:
    """Collects data either from local static files or the live internet."""

    # mock mode
    if SCAN_MODE == "MOCK":
        logger.info(f"[URLScan] Running in MOCK mode for {domain}")
        mock_file = WORKERS_ROOT / "docs" / "raw_samples" / "UrlScan_Response.json"

        try:
            with open(mock_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("X Mock file not found. Returning empty dict.")
            return {}

    # live mode
    logger.info(f"[URLScan] Running in LIVE mode for {domain}")

    if not URLSCAN_API_KEY or URLSCAN_API_KEY == "fake_key_1234":
        logger.error("X LIVE mode requires valid URLSCAN_API_KEY in the .env file.")
        return {"error": "Missing URLScan API Key"}

    headers = {"API-Key": URLSCAN_API_KEY, "Content-Type": "application/json"}
    payload = {"url": f"https://{domain}", "visibility": "public"}

    with httpx.Client() as client:
        # Submit the Scan
        submit_url = "https://urlscan.io/api/v1/scan/"
        logger.info(f"[URLScan] Submitting {domain} to URLScan infrastructure...")

        try:
            submit_res = client.post(submit_url, headers=headers, json=payload, timeout=15.0)
            submit_res.raise_for_status()

        # expand the types of errors not just STATUS errors
        except httpx.HTTPError as e:
            logger.exception(f"URLScan API Error: {e}")  # catch timeouts
            return {"error": "API Request Failed"}
        try:
            uuid = submit_res.json().get("uuid")
        except ValueError as e:
            logger.exception(f"URLScan API Error: {e}")
            return {"error": "Invalid API Response"}
        logger.info(f"[URLScan] Scan queued. UUID: {uuid}. Entering polling loop...")

        # poll for results every 10 seconds, up to 6 attempts. 1 min total
        result_url = f"https://urlscan.io/api/v1/result/{uuid}/"
        raw_result = {}

        poll_attempts = 4
        poll_interval_seconds = 7

        for attempt in range(poll_attempts):
            time.sleep(poll_interval_seconds)
            logger.info(f"[URLScan] Polling for results (Attempt {attempt + 1}/6)...")
            res = client.get(result_url,headers=headers, timeout=10.0)
            
            if res.status_code == 200:
                raw_result = res.json()
                logger.info("[URLScan] Scan complete and data retrieved!")
                break
            elif res.status_code == 404:
                continue  # Scan is still running, keep waiting
            else:
                logger.error(f"[URLScan] Unexpected API response: {res.status_code}")
                return {"error": f"API Error {res.status_code}"}

        if not raw_result:
            logger.error("[URLScan] X Scan timed out after 60 seconds.")
            return {"error": "Scan Timeout"}

        # download screen shot to our local templates folder
        # for PDF report generation (and potential future DB storage)
        screenshot_url = f"https://urlscan.io/screenshots/{uuid}.png"
        filename = f"{domain.replace('.', '_')}_{uuid}.png"
        saved_filename = _download_screenshot(screenshot_url, filename)

        # Inject our local filename into their massive JSON payload
        raw_result["_local_screenshot_path"] = saved_filename
        return raw_result


def normalize_data(raw_data: dict) -> dict:
    """
    Flattens either the Mock JSON or the massive Live JSON into our contract.
    """

    if "error" in raw_data:
        return {
            "reputation": {
                "provider": "URLScan",
                "malicious_flags": 0,
                "urlscan_uuid": "Unknown",
                "screenshot_url": DEFAULT_SCREENSHOT,
                "error": raw_data["error"],
            }
        }

    logger.info("Normalizing URLScan data (Production Mode):")

    is_live_data = "verdicts" in raw_data

    if is_live_data:
        # Extract from URLScan's actual JSON structure
        is_malicious = raw_data.get("verdicts", {}).get("overall", {}).get("malicious", False)
        return {
            "reputation": {
                "provider": "URLScan",
                "malicious_flags": 1 if is_malicious else 0,
                "urlscan_uuid": raw_data.get("task", {}).get("uuid", "Unknown"),
                "screenshot_url": raw_data.get("_local_screenshot_path", DEFAULT_SCREENSHOT),
            }
        }
    else:
        # Extract from our flat Mock JSON structure
        return {
            "reputation": {
                "provider": raw_data.get("provider", "URLScan"),
                "malicious_flags": raw_data.get("malicious_flags", 0),
                "urlscan_uuid": raw_data.get("urlscan_uuid", "Unknown"),
                "screenshot_url": raw_data.get("screenshot_url", DEFAULT_SCREENSHOT),
            }
        }


# findings
def generate_findings(normalized_data: dict) -> list:
    findings = []
    reputation = normalized_data.get("reputation", {})
    if reputation.get("malicious_flags", 0) > 0:
        findings.append(
            {
                "source": "urlscan",
                "severity": "high",
                "title": "Malicious Activity Detected by URLScan",
                "description": ("URLScan flagged this domain for malicious behavior or phishing."),
                "recommendation": (
                    "Immediately investigate the domain for compromised hosting or DNS hijacking."
                ),
                "evidence": normalized_data,
            }
        )
    return findings
