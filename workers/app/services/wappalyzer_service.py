import logging
import os
import logging
import httpx
import json
from pathlib import Path  

#Logger to tell us this file was in error
logger = logging.getLogger(__name__)

SCAN_MODE = os.getenv("SCAN_MODE", "MOCK").upper()
WAPPALYZER_API_KEY = os.getenv("WAPPALYZER_API_KEY", "fake_key_1234")
WORKERS_ROOT = Path(__file__).resolve().parent.parent.parent

#collect the raw data from wappalyzer api or from mock file depending on mode
def collect_raw_data(domain: str) -> dict:
    """Collects technology stack data from Wappalyzer (Mock or Live)."""
    
    #Mock mode
    if SCAN_MODE == "MOCK":
        logger.info(f"[Wappalyzer] Running in MOCK mode for {domain}")
        safeDomain = domain.replace(".", "_")
        mockFile = WORKERS_ROOT / "docs" / "raw_samples" / f"Wappalyzer_{safeDomain}.json"
        
        if not mockFile.exists():
            mockFile = WORKERS_ROOT / "docs" / "raw_samples" / "Wappalyzer_Response.json"
            
        try:
            with open(mockFile, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("X Mock file not found. Returning empty dict.")
            return {}

    #Live Mode
    logger.info(f"[Wappalyzer] Running in FULL LIVE mode for {domain}")
    
    if not WAPPALYZER_API_KEY or WAPPALYZER_API_KEY == "fake_key_1234":
        logger.error("X LIVE mode requires a valid WAPPALYZER_API_KEY in the .env file!")
        return {"error": "Missing Wappalyzer API Key"}

    #Query Wappalyzer
    url = f"https://api.wappalyzer.com/lookup/v2/?urls=https://{domain}"
    headers = \
    {
        "x-api-key": WAPPALYZER_API_KEY
    }
    
    with httpx.Client() as client:
        try:
            res = client.get(url, headers=headers, timeout=15.0)
            res.raise_for_status()
            
            #wappalyzer returns a list of results (one per URL scanned). we just want the first one.
            data = res.json()
            if data and isinstance(data, list):
                return data[0]
            return {}
            
        except httpx.HTTPError as e:
            logger.error(f"X Wappalyzer API Error: {e}")
            return {"error": "API Request Failed"}

def normalize_wappalyzer_data(raw_data: dict) -> dict:
    """
    Extracts tech stack information from raw Wappalyzer JSON.
    Returns a dictionary matching the PenFlow Data Contract Schema.
    """
    logger.info("Normalizing Wappalyzer data (Expanded):")
    
    # Initialize empty lists for our expanded schema categories
    cms = []
    frameworks = []
    webServers = []
    paas = []
    programmingLanguages = []
    databases = []
    cdns = []

    # In this format:
    # the key is the tech name, and the value holds the details
    for techName, techDetails in raw_data.items():
        
        # Extract version safely
        versionsList = techDetails.get("versions", [])
        if len(versionsList) > 0:
            version = versionsList[0]
        else:
            version = "Unknown"

        techObj = \
        {
            "name": techName,
            "version": version
        }

        # Categories come directly as a list of strings
        categories = techDetails.get("categories", [])
        
        # Sort the technology into our unified schema categories
        for category in categories:
            if "CMS" in category:
                cms.append(techObj)
            elif "Web frameworks" in category or "JavaScript frameworks" in category:
                frameworks.append(techObj)
            elif "Web servers" in category:
                webServers.append(techObj)
            elif "PaaS" in category:
                paas.append(techObj)
            elif "Programming languages" in category:
                programmingLanguages.append(techObj)
            elif "Databases" in category:
                databases.append(techObj)
            elif "CDN" in category:
                cdns.append(techObj)

    # Our strict data contract schema format
    final_result = \
    {
        "provider": "Wappalyzer",
        "cms": cms,
        "frameworks": frameworks,
        "webServers": webServers,
        "paas": paas,
        "programmingLanguages": programmingLanguages,
        "databases": databases,
        "cdns": cdns
    }

    return final_result