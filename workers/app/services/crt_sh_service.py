import json
import logging
import os
import time
from pathlib import Path

import httpx

# Logger to track this specific worker
logger = logging.getLogger(__name__)
CRT_SH_PROVIDER = "crt.sh"
SCAN_MODE = os.getenv("SCAN_MODE", "MOCK").upper()
WORKERS_ROOT = Path(__file__).resolve().parent.parent.parent

#collect raw data from mocks or from crt.sh depending on mode
def fetch_mock_data(domain: str) -> dict:
    """Collects subdomain and certificate data from crt.sh (Mock or Live)."""
    
    #Mock mode
    if SCAN_MODE == "MOCK":
        logger.info(f"[CRT.sh] Running in MOCK mode for {domain}")
        safe_domain = domain.replace(".", "_")
        mock_file = WORKERS_ROOT / "docs" / "raw_samples" / f"CrtSh_{safe_domain}.json"
        
        if not mock_file.exists():
            mock_file = WORKERS_ROOT / "docs" / "raw_samples" / "CrtSh_Response.json"
            
        try:
            with open(mock_file, "r") as f:
                data = json.load(f)
                #wrap the raw list in a dictionary so our pipeline stays consistent
                return {
                    "certificates": data
                }
        except FileNotFoundError:
            logger.error("X Mock file not found. Returning empty dict.")
            return {"certificates": []}
    return{}


def fetch_live_data(domain: str) -> dict:
    #Live Mode
    logger.info(f"[CRT.sh] Running in FULL LIVE mode for {domain}")
    
    #crt.sh is a free public database, we need no api key
    #we use %.domain to get all subdomains
    url = f"https://crt.sh/?q=%.{domain}&output=json&exclude=expired"
    

    #crt.sh is very bad with reliable requests, 
    #we have to do a lot of retry logic to try get a good response.
    max_attempts = 3
    timeout_seconds = 8.0
    retry_delay_seconds = 3

    
    with httpx.Client() as client:
        for attempt in range(1, max_attempts + 1):
            logger.info(
                f"[CRT.sh] Polling database (Attempt {attempt}/{max_attempts}) "
                f"with {timeout_seconds}s timeout...")
            try:
                #crt.sh can be slow to respond, so we set a long timeout
                res = client.get(url, timeout=timeout_seconds)

                # Catch 502 Bad Gateway / 503 Service Unavailable natively
                if res.status_code in [502, 503, 504]:
                    logger.warning(f"[CRT.sh] Server returned {res.status_code}. Retrying...")
                    
                else:
                    res.raise_for_status()
                    # crt.sh sometimes returns a completely blank page when it struggles
                    if not res.text.strip():
                        logger.warning("[CRT.sh] Returned a blank response. Retrying...")
                    else:
                        try:
                            return {
                                "certificates": res.json()
                            }
                        # Try to parse the JSON. If it's half-broken, catch it and retry.
                        except json.JSONDecodeError:
                            logger.warning(
                                "[CRT.sh] Request timed out after %.1fs.",
                                timeout_seconds,
                            )
                
            except httpx.TimeoutException:
                logger.warning(f"[CRT.sh] Timeout reached ({timeout_seconds}s). Retrying...")

            except httpx.HTTPError as e:
                logger.warning(f"[CRT.sh] HTTP Error: {e}. Retrying...")

            if attempt < max_attempts:
                time.sleep(retry_delay_seconds)
            
        # If we exhaust all 5 attempts, fail gracefully
        logger.error(f"[CRT.sh] X Completely failed after {max_attempts} attempts.")
        return {"error": "API Request Failed / Timed Out"}
    
def collect_raw_data(domain: str) -> dict:
    """Collects subdomain and certificate data from crt.sh (Mock or Live)."""
    if SCAN_MODE == "MOCK":
        return fetch_mock_data(domain)
    
    return fetch_live_data(domain)    

def normalize_data(raw_data: dict) -> dict:
    """
    Extracts and normalizes subdomains from raw crt.sh JSON.
    Removes all duplicates.
    """

    if "error" in raw_data:
        return {
            "subdomains": {
                "provider": CRT_SH_PROVIDER,
                "total_found": 0,
                "discovered_names": [],
                "error": raw_data.get("error"),
            }
        }
    
    logger.info("Normalizing crt.sh data:")
    
    unique_subdomains = set()
    certificates = raw_data.get("certificates", [])

    for cert in certificates:
        # Safe extraction of the domain string
        name_value = cert.get("name_value", "")
        split_names = name_value.split("\n")
        
        for name in split_names:
            name = name.strip().lower()
            if name and not name.startswith("*."):
                unique_subdomains.add(name)
                

    # Convert the set back to a sorted list so the JSON output is consistent and readable
    discovered_names = sorted(unique_subdomains)
    
    #format it into our strict schema
    normalized_subdomains = []
    for sub in discovered_names:
        normalized_subdomains.append(
        {
            "subdomain": sub
        })
        
    return {
        "subdomains": {
            "provider": CRT_SH_PROVIDER,
            "total_found": len(discovered_names),
            "discovered_names": discovered_names,
    }
}

#analyze subdomains for potential risks and extract assets
def generate_findings_and_assets(normalized_data: dict) -> tuple:
    findings = []
    assets = []
    
    subdomains = normalized_data.get("subdomains", {})

    if "error" in subdomains:
        return findings, assets
    
    for subdomain in subdomains.get("discovered_names", []):
        assets.append({
            "asset_type": "subdomain",
            "identifier": subdomain,
            "asset_metadata": {
                "source": CRT_SH_PROVIDER,
            },
        })
            
    return findings, assets

