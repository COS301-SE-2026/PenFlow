import logging
import os
import json
import httpx
from pathlib import Path


#logger to tell is this file was in error
logger = logging.getLogger(__name__)

SCAN_MODE = os.getenv("SCAN_MODE", "MOCK")
HIBP_API_KEY = os.getenv("HIBP_API_KEY", "fake_key_1234")
WORKERS_DIR = Path(__file__).resolve().parent.parent.parent

#collect raw data from mocks or from HIBP api depending on mode
def collect_raw_data(domain: str) -> dict:
    """Collects historical breach data from HaveIBeenPwned (Mock or Live)."""
    
    #Mock mode
    if SCAN_MODE == "MOCK":
        logger.info(f"[HIBP] Running in MOCK mode for {domain}")
        safeDomain = domain.replace(".", "_")
        mockFile = WORKERS_DIR / "docs" / "raw_samples" / f"Hibp_{safeDomain}.json"
        
        if not mockFile.exists():
            mockFile = WORKERS_DIR / "docs" / "raw_samples" / "Hibp_Response.json"
            
        try:
            with open(mockFile, "r") as f:
                data = json.load(f)
                return {"breaches": data}
        except FileNotFoundError:
            logger.error("X Mock file not found. Returning empty dict.")
            return {"breaches": []}

    #Live Mode
    logger.info(f"[HIBP] Running in FULL LIVE mode for {domain}")
    
    if not HIBP_API_KEY or HIBP_API_KEY == "fake_key_1234":
        logger.error("X LIVE mode requires a valid HIBP_API_KEY in the .env file!")
        return {"error": "Missing HIBP API Key"}

    url = f"https://haveibeenpwned.com/api/v3/breaches?domain={domain}"
    
    #HIBP requires the API key in a specific header and a custom User-Agent
    headers = \
    {
        "hibp-api-key": HIBP_API_KEY,
        "user-agent": "PenFlow-Security-Worker"
    }
    
    with httpx.Client() as client:
        try:
            res = client.get(url, headers=headers, timeout=15.0)
            
            # 404 means no breaches were found for this domain
            if res.status_code == 404:
                return {"breaches": []}
                
            res.raise_for_status()
            return {"breaches": res.json()}
            
        except httpx.HTTPError as e:
            logger.error(f"X HIBP API Error: {e}")
            return {"error": "API Request Failed"}
        

def normalize_data(rawData: list) -> dict:
    """
    Normalizes breach data from a raw HaveIBeenPwned response payload.
    """
    
    logger.info("Normalizing HIBP breach data:")
    if "error" in rawData:
        return {"error": rawData["error"]}
    breaches = rawData.get("breaches", [])
    knownBreaches = []
    
    for breach in breaches:
        breachName = breach.get("Name")
        if breachName:
            knownBreaches.append(breachName)
    knownBreaches.sort()
    
    return \
    {
        "provider": "HaveIBeenPwned",
        "pwned_accounts_count": len(knownBreaches),
        "known_breaches": knownBreaches
    }