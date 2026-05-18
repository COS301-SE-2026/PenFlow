import logging
import os
from pathlib import Path
import json
import httpx

# Logger to track this specific worker
logger = logging.getLogger(__name__)
SCAN_MODE = os.getenv("SCAN_MODE", "MOCK").upper()
WORKERS_ROOT = Path(__file__).resolve().parent.parent.parent

#collect raw data from mocks or from crt.sh depending on mode
def collect_raw_data(domain: str) -> dict:
    """Collects subdomain and certificate data from crt.sh (Mock or Live)."""
    
    #Mock mode
    if SCAN_MODE == "MOCK":
        logger.info(f"[CRT.sh] Running in MOCK mode for {domain}")
        safeDomain = domain.replace(".", "_")
        mockFile = WORKERS_ROOT / "docs" / "raw_samples" / f"CrtSh_{safeDomain}.json"
        
        if not mockFile.exists():
            mockFile = WORKERS_ROOT / "docs" / "raw_samples" / "CrtSh_Response.json"
            
        try:
            with open(mockFile, "r") as f:
                data = json.load(f)
                #wrap the raw list in a dictionary so our pipeline stays consistent
                return \
                {
                    "certificates": data
                }
        except FileNotFoundError:
            logger.error("X Mock file not found. Returning empty dict.")
            return {"certificates": []}

    #Live Mode
    logger.info(f"[CRT.sh] Running in FULL LIVE mode for {domain}")
    
    #crt.sh is a free public database, we need no api key
    #we use %.domain to get all subdomains
    url = f"https://crt.sh/?q=%.{domain}&output=json"
    
    #crt.sh often blocks default python user-agents, so we spoof a real one
    headers = \
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    with httpx.Client() as client:
        try:
            #crt.sh can be slow to respond, so we set a long timeout
            res = client.get(url, headers=headers, timeout=45.0)
            res.raise_for_status()
            
            return \
            {
                "certificates": res.json()
            }
            
        except httpx.HTTPError as e:
            logger.error(f"X CRT.sh API Error: {e}")
            return {"error": "API Request Failed"}

def normalize_data(rawData: list) -> dict:
    """
    Extracts and normalizes subdomains from raw crt.sh JSON.
    Removes all duplicates.
    """

    if "error" in rawData:
        return {"error": rawData["error"]}
    
    logger.info("Normalizing crt.sh data:")
    
    uniqueSubdomains = set()
    certificates = rawData.get("certificates", [])

    for cert in certificates:
        # Safe extraction of the domain string
        nameValue = cert.get("name_value", "")
        splitNames = nameValue.split("\n")
        
        for name in splitNames:
            name = name.strip().lower()
            if name and not name.startswith("*."):
                uniqueSubdomains.add(name)
                

    # Convert the set back to a sorted list so the JSON output is consistent and readable
    discoveredNames = sorted(list(uniqueSubdomains))
    
    #format it into our strict schema
    normalizedSubdomains = []
    for sub in discoveredNames:
        normalizedSubdomains.append(
        {
            "subdomain": sub
        })
        
    return \
    {
        "subdomains": normalizedSubdomains
    }