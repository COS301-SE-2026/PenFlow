import logging
import os
import json
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
    if SCAN_MODE == "MOCK":
        logger.info(f"[Hunter] Running in MOCK mode for {domain}")
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
    
    if not HUNTER_API_KEY or HUNTER_API_KEY == "fake_key_123456789":
        logger.error("X LIVE mode requires a valid HUNTER_API_KEY in the .env file!")
        return {"error": "Missing Hunter API Key"}

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

def normalize_hunter_data(rawData: dict) -> dict:
    """
    Extracts email formats and employee addresses from raw Hunter.io JSON.
    Strips superfluous info so we only get a list of targets to process.
    """
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
        # We only care about the email, type, and confidence score.
        # We intentionally ignore the rest of the marketing metadata to save DB space.
        emailAddress = emp.get("value", "Unknown")
        emailType = emp.get("type", "Unknown")
        confidence = emp.get("confidence", 0)

        # Skip entries that are completely broken
        if emailAddress == "Unknown":
            continue

        emailObj = \
        {
            "email": emailAddress,
            "type": emailType,
            "confidence_score": confidence
        }
        
        formattedEmails.append(emailObj)

    # Our strict data contract schema format for the Phishing Surface section
    final_result = \
    {
        "provider": "Hunter.io",
        "email_format_pattern": pattern,
        "public_emails_found": formattedEmails
    }

    return final_result