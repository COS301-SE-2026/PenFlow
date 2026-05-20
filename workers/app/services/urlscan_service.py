import logging
import json
import os
from celery import shared_task
import httpx
from pathlib import Path
import time

# Logger to track this specific worker
logger = logging.getLogger(__name__)

#scan mode between live and mock
SCAN_MODE = os.getenv("SCAN_MODE", "MOCK").upper()
URLSCAN_API_KEY = os.getenv("URLSCAN_API_KEY", "fake_key_1234")

WORKERS_ROOT = Path(__file__).resolve().parent.parent.parent

TEMPLATES_DIR = WORKERS_ROOT.parent / "backend" / "app" / "templates"

#so we can display screen shot
def _download_screenshot(image_url: str, targetFilename: str) -> str:
    """Downloads an image from the web and saves it to the shared templates folder."""
    try:
        logger.info(f"Downloading live screenshot from: {image_url}")
        TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        response = httpx.get(image_url, timeout=15.0)
        response.raise_for_status()

        # Save it directly where the PDF engine expects to find it
        savePath = TEMPLATES_DIR / targetFilename
        with open(savePath, "wb") as f:
            f.write(response.content)

        logger.info(f"Screenshot saved successfully as: {targetFilename}")
        return targetFilename
    except Exception as e:
        logger.error(f"X Failed to download screenshot: {e}")

        #default for failure for now
        return "brocode_logo.png"
    

def collect_raw_data(domain: str) -> dict:
    """Collects data either from local static files or the live internet."""
    
    #mock mode
    if SCAN_MODE == "MOCK":
        logger.info(f"[URLScan] Running in MOCK mode for {domain}")
        mockFile = WORKERS_ROOT / "docs" / "raw_samples" / "UrlScan_Response.json"
        
        try:
            with open(mockFile, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("X Mock file not found. Returning empty dict.")
            return {}

    #live mode
    logger.info(f"[URLScan] Running in LIVE mode for {domain}")
    
    if not URLSCAN_API_KEY or URLSCAN_API_KEY == "fake_key_1234":
        logger.error("X LIVE mode requires valid URLSCAN_API_KEY in the .env file.")
        return {"error": "Missing URLScan API Key"}

    headers = {"API-Key": URLSCAN_API_KEY, "Content-Type": "application/json"}
    payload = {"url": f"https://{domain}", "visibility": "public"}
    
    with httpx.Client() as client:
        #Submit the Scan
        submitUrl = "https://urlscan.io/api/v1/scan/"
        logger.info(f"[URLScan] Submitting {domain} to URLScan infrastructure...")
        
        try:
            submitRes = client.post(submitUrl, headers=headers, json=payload, timeout=15.0)
            submitRes.raise_for_status()
            
        #expand the types of errors not just STATUS errors
        except httpx.HTTPError as e:
            logger.error(f"URLScan API Error: {e}")#catch timeouts
            return {"error": "API Request Failed"}
        try:    
            uuid = submitRes.json().get("uuid")
        except ValueError as e:
            logger.error(f"URLScan API Error: {e}")
            return {"error": "Invalid API Response"}
        logger.info(f"[URLScan] Scan queued. UUID: {uuid}. Entering polling loop...")

        #poll for results every 10 seconds, up to 6 attempts. 1 min total
        resultUrl = f"https://urlscan.io/api/v1/result/{uuid}/"
        raw_result = {}
        
        for attempt in range(6):
            time.sleep(10)
            logger.info(f"[URLScan] Polling for results (Attempt {attempt + 1}/6)...")
            res = client.get(resultUrl,headers=headers, timeout=15.0)
            
            if res.status_code == 200:
                raw_result = res.json()
                logger.info("[URLScan] Scan complete and data retrieved!")
                break
            elif res.status_code == 404:
                continue # Scan is still running, keep waiting
            else:
                logger.error(f"[URLScan] Unexpected API response: {res.status_code}")
                return {"error": f"API Error {res.status_code}"}

        if not raw_result:
            logger.error("[URLScan] X Scan timed out after 60 seconds.")
            return {"error": "Scan Timeout"}

        #download screen shot to our local templates folder for PDF report generation (and potential future DB storage)
        screenshotUrl = f"https://urlscan.io/screenshots/{uuid}.png"
        filename = f"{domain.replace('.', '_')}_{uuid}.png"
        savedFilename = _download_screenshot(screenshotUrl, filename)

        # Inject our local filename into their massive JSON payload
        raw_result["_local_screenshot_path"] = savedFilename
        return raw_result
       

def normalize_data(rawData: dict) -> dict:
    """
    Flattens either the Mock JSON or the massive Live JSON into our contract.
    """

    if "error" in rawData:
        return {"provider": "URLScan", "error": rawData["error"]}
    logger.info("Normalizing URLScan data (Production Mode):")

    isLiveData = "verdicts" in rawData
    

    if isLiveData:
        # Extract from URLScan's actual JSON structure
        is_malicious = rawData.get("verdicts", {}).get("overall", {}).get("malicious", False)
        return {
            "provider": "URLScan",
            "malicious_flags": 1 if is_malicious else 0,
            "urlscan_uuid": rawData.get("task", {}).get("uuid", "Unknown"),
            "screenshot_url": rawData.get("_local_screenshot_path", "default.png")
        }
    else:
        # Extract from our flat Mock JSON structure
        return {
            "provider": rawData.get("provider", "URLScan"),
            "malicious_flags": rawData.get("malicious_flags", 0),
            "urlscan_uuid": rawData.get("urlscan_uuid", "Unknown"),
            "screenshot_url": rawData.get("screenshot_url", "default.png")
        }

#findings
def generate_findings(normalizedData: dict) -> list:
    findings = []
    if normalizedData.get("malicious_flags", 0) > 0:
        findings.append({
            "source": "urlscan",
            "severity": "high",
            "title": "Malicious Activity Detected by URLScan",
            "description": "URLScan flagged this domain for malicious behavior or phishing.",
            "recommendation": "Immediately investigate the domain for compromised hosting or DNS hijacking.",
            "evidence": normalizedData
        })
    return findings    

#execution
@shared_task(name="scan.urlscan")
def run_urlscan(domain: str) -> dict:
    raw_data = collect_raw_data(domain)
    normalized = normalize_data(raw_data)
    findings = generate_findings(normalized)

    return \
    {
        "source_name": "urlscan",
        "status": "completed" if "error" not in normalized else "failed",
        "raw_result": {"reputation": normalized},
        "findings": findings,
        "assets": []
    }
