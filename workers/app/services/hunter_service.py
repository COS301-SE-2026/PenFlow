import json
import logging
import os
from pathlib import Path

import httpx

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
        safe_domain = domain.replace(".", "_")
        mock_file = WORKERS_ROOT / "docs" / "raw_samples" / f"Hunter_{safe_domain}.json"
        
        if not mock_file.exists():
            mock_file = WORKERS_ROOT / "docs" / "raw_samples" / "Hunter_Response.json"
            
        try:
            with open(mock_file, "r") as f:
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
            logger.exception(f"X Hunter API Error: {e}")
            return {"error": "API Request Failed"}

def normalize_data(raw_data: dict) -> dict:
    """
    Extracts email formats and employee addresses from raw Hunter.io JSON.
    Strips superfluous info so we only get a list of targets to process.
    """
    if "error" in raw_data:
        return {"error": raw_data["error"]}
    logger.info("Normalizing Hunter.io data:")
    
    # Hunter.io wraps their actual payload inside a "data" key in accordance to their documentation
    data_block = raw_data.get("data", {})
    
    # Extract the email pattern so pentesting tools can guess other emails
    pattern = data_block.get("pattern", "Unknown")
    
    # Safely get the list of emails
    raw_emails = data_block.get("emails", [])
    formatted_emails = []

    # Iterate through each employee entry
    for emp in raw_emails:
        formatted_emails.append(
        {
            "email": emp.get("value", "Unknown"),
            "type": emp.get("type", "Unknown"),
            "confidence_score": emp.get("confidence", 0)
        })


    return \
    {
        "phishing_surface": {
            "provider": "Hunter.io",
            "email_format_pattern": pattern,
            "public_emails_found": formatted_emails,
        }
    }

#analyze emails for potential risks and extract assets
def generate_findings_and_assets(normalized_data: dict) -> tuple:
    findings = []
    assets = []
    
    if "error" in normalized_data:
        return findings, assets
        
    phishing_surface = normalized_data.get("phishing_surface", {})
    emails_found = phishing_surface.get("public_emails_found", [])
    
    for email_obj in emails_found:
        email_address = email_obj.get("email")
        
        # Add every discovered email to the PenFlow Asset inventory
        if email_address and email_address != "Unknown":
            assets.append(
            {
                "asset_type": "email",
                "identifier": email_address,
                "source": "hunter.io"
            })
            
    # If we found emails, flag it for the phishing simulation team
    if assets:
        findings.append(
        {
            "source": "hunter.io",
            "severity": "info",
            "title": f"Discovered {len(assets)} Public Email Addresses",
            "description": ("Publicly accessible email addresses were discovered for this domain."
            " These are prime targets for social engineering or spear-phishing campaigns."),
            "recommendation": ("Ensure all staff undergo regular phishing awareness training "
            "and implement strict email filtering."),
            "evidence": {"email_count": len(assets), 
            "pattern": phishing_surface.get("email_format_pattern")}
        })
            
    return findings, assets

