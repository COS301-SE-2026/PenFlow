import logging
import os
from pathlib import Path
import json
import httpx
import time
from celery import shared_task

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
    url = f"https://crt.sh/?q=%.{domain}&output=json&exclude=expired"
    

    #crt.sh is very bad with reliable requests, we have to do a lot of retry logic to try get a good response.
    max_attempts = 6
    timeout_seconds = 15.0

    
    with httpx.Client() as client:
        for attempt in range(1, max_attempts + 1):
            logger.info(f"[CRT.sh] Polling database (Attempt {attempt}/{max_attempts}) with {timeout_seconds}s timeout...")
            try:
                #crt.sh can be slow to respond, so we set a long timeout
                res = client.get(url, timeout=timeout_seconds)

                # Catch 502 Bad Gateway / 503 Service Unavailable natively
                if res.status_code in [502, 503, 504]:
                    logger.warning(f"[CRT.sh] Server returned {res.status_code}. Retrying...")
                    time.sleep(3)
                    continue
                    
                res.raise_for_status()
                
                # crt.sh sometimes returns a completely blank page when it struggles
                if not res.text.strip():
                    logger.warning("[CRT.sh] Returned a blank response. Retrying...")
                    time.sleep(3)
                    continue

                # Try to parse the JSON. If it's half-broken, catch it and retry.
                try:
                    return {"certificates": res.json()}
                except json.JSONDecodeError:
                    logger.warning("[CRT.sh] Returned invalid JSON. Retrying...")
                    time.sleep(3)
                    continue
                
            except httpx.ReadTimeout:
                logger.warning(f"[CRT.sh] Timeout reached ({timeout_seconds}s). Retrying...")
                time.sleep(3)
            except httpx.HTTPError as e:
                logger.warning(f"[CRT.sh] HTTP Error: {e}. Retrying...")
                time.sleep(3)
             
            
        # If we exhaust all 5 attempts, fail gracefully
        logger.error(f"[CRT.sh] X Completely failed after {max_attempts} attempts.")
        return {"error": "API Request Failed / Timed Out"}

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

#analyze subdomains for potential risks and extract assets
def generate_findings_and_assets(normalizedData: dict) -> tuple:
    findings = []
    assets = []
    
    if "error" in normalizedData:
        return findings, assets
        
    for subObj in normalizedData.get("subdomains", []):
        subdomain = subObj.get("subdomain")
        
        # Add every discovered subdomain to the PenFlow Asset inventory
        if subdomain:
            assets.append(
            {
                "asset_type": "subdomain",
                "value": subdomain,
                "source": "crt_sh"
            })
            
    return findings, assets


#execution
@shared_task(name="scan.crt_sh")
def run_crt_sh(domain: str) -> dict:
    rawData = collect_raw_data(domain)
    normalized = normalize_data(rawData)
    findings, assets = generate_findings_and_assets(normalized)
    
    # Extract just the string names for the PDF builder's expected format
    discoveredNames = []
    for sub in normalized.get("subdomains", []):
        discoveredNames.append(sub.get("subdomain"))
    
    return \
    {
        "source_name": "crt_sh",
        "status": "completed" if "error" not in normalized else "failed",
        "raw_result": 
        {
            "provider": "crt.sh",
            "total_found": len(discoveredNames),
            "discovered_names": discoveredNames
        },
        "findings": findings,
        "assets": assets
    }