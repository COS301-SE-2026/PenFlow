import logging
import os
import json
from celery import shared_task
import httpx
from pathlib import Path

# Logger to track this specific worker
logger = logging.getLogger(__name__)
SCAN_MODE = os.getenv("SCAN_MODE", "MOCK").upper()
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "fake_key_123456789")
WORKERS_ROOT = Path(__file__).resolve().parent.parent.parent

#collect raw data from mocks or from hunter api depending on mode
def collect_raw_data(domain: str) -> dict:
    """Collects exposed email data from Hunter.io (Mock or Live)."""
    
    #Mock mode
    if SCAN_MODE == "MOCK" or not HUNTER_API_KEY or "fake" in HUNTER_API_KEY.lower():
        logger.info(f"[Hunter] Running in MOCK/Demo mode for {domain}")
        safeDomain = domain.replace(".", "_")
        mockFile = WORKERS_ROOT / "docs" / "raw_samples" / f"Hunter_{safeDomain}.json"
        
        if not mockFile.exists():
            mockFile = WORKERS_ROOT / "docs" / "raw_samples" / "Hunter_Response.json"
            
        try:
            with open(mockFile, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("X Mock file not found. Returning empty dict.")
            return {}

    #Live Mode
    logger.info(f"[Hunter] Running in FULL LIVE mode for {domain}")

    #Query Hunter.io Domain Search API
    url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={HUNTER_API_KEY}"
    
    with httpx.Client() as client:
        try:
            res = client.get(url, timeout=15.0)
            
            # Hunter returns 404 if no emails are found.not an error just means empty
            if res.status_code == 404:
                return {"data": {"emails": [], "pattern": None}}
                
            res.raise_for_status()
            return res.json()
            
        except httpx.HTTPError as e:
            logger.error(f"X Hunter API Error: {e}")
            return {"error": "API Request Failed"}

def normalize_data(rawData: dict) -> dict:
    """
    Extracts email formats and employee addresses from raw Hunter.io JSON.
    Strips superfluous info so we only get a list of targets to process.
    """
    if "error" in rawData:
        return {"error": rawData["error"]}
    logger.info("Normalizing Hunter.io data:")
    
    # Hunter.io wraps their actual payload inside a "data" key in accordance to their documentation
    dataBlock = rawData.get("data", {})
    
    # Extract the email pattern so pentesting tools can guess other emails
    pattern = dataBlock.get("pattern", "Unknown")
    
    # Safely get the list of emails
    rawEmails = dataBlock.get("emails", [])
    formattedEmails = []

    # Iterate through each employee entry
    for emp in rawEmails:
        formattedEmails.append(
        {
            "email": emp.get("value", "Unknown"),
            "type": emp.get("type", "Unknown"),
            "confidence_score": emp.get("confidence", 0)
        })


    return \
    {
            "provider": "Hunter.io",
        "email_format_pattern": pattern,
        "public_emails_found": formattedEmails
    }

#analyze emails for potential risks and extract assets
def generate_findings_and_assets(normalizedData: dict) -> tuple:
    findings = []
    assets = []
    
    if "error" in normalizedData:
        return findings, assets
        
    emailsFound = normalizedData.get("public_emails_found", [])
    
    for emailObj in emailsFound:
        emailAddress = emailObj.get("email")
        
        # Add every discovered email to the PenFlow Asset inventory
        if emailAddress and emailAddress != "Unknown":
            assets.append(
            {
                "asset_type": "email",
                "value": emailAddress,
                "source": "hunter"
            })
            
    # If we found emails, flag it for the phishing simulation team
    if assets:
        findings.append(
        {
            "source": "hunter",
            "severity": "info",
            "title": f"Discovered {len(assets)} Public Email Addresses",
            "description": "Publicly accessible email addresses were discovered for this domain. These are prime targets for social engineering or spear-phishing campaigns.",
            "recommendation": "Ensure all staff undergo regular phishing awareness training and implement strict email filtering.",
            "evidence": {"email_count": len(assets), "pattern": normalizedData.get("email_format_pattern")}
        })
            
    return findings, assets


#execution
@shared_task(name="scan.hunter")
def run_hunter(domain: str) -> dict:
    rawData = collect_raw_data(domain)
    normalized = normalize_data(rawData)
    findings, assets = generate_findings_and_assets(normalized)
    
    return \
    {
        "source_name": "hunter",
        "status": "completed" if "error" not in normalized else "failed",
        "raw_result": normalized,
        "findings": findings,
        "assets": assets
    }