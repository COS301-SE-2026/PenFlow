import json
import logging
import os
from pathlib import Path

import httpx
from celery import shared_task

#logger to tell is this file was in error
logger = logging.getLogger(__name__)

SCAN_MODE = os.getenv("SCAN_MODE", "MOCK")
HIBP_API_KEY = os.getenv("HIBP_API_KEY", "fake_key_1234")
WORKERS_DIR = Path(__file__).resolve().parent.parent.parent

#collect raw data from mocks or from HIBP api depending on mode
def collect_raw_data(domain: str) -> dict:
    """Collects historical breach data from HaveIBeenPwned (Mock or Live)."""
    
    #Mock mode
    if SCAN_MODE == "MOCK" or not HIBP_API_KEY or "fake" in HIBP_API_KEY.lower():
        logger.info(f"[HIBP] Running in MOCK/Demo mode for {domain}")
        safe_domain = domain.replace(".", "_")
        mock_file = WORKERS_DIR / "docs" / "raw_samples" / f"Hibp_{safe_domain}.json"
        
        if not mock_file.exists():
            mock_file = WORKERS_DIR / "docs" / "raw_samples" / "Hibp_Response.json"
            
        try:
            with open(mock_file, "r") as f:
                data = json.load(f)
                return {"breaches": data}
        except FileNotFoundError:
            logger.error("X Mock file not found. Returning empty dict.")
            return {"breaches": []}

    #Live Mode
    logger.info(f"[HIBP] Running in FULL LIVE mode for {domain}")

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
            logger.exception(f"X HIBP API Error: {e}")
            return {"error": "API Request Failed"}
        

def normalize_data(raw_data: list) -> dict:
    """
    Normalizes breach data from a raw HaveIBeenPwned response payload.
    """
    
    logger.info("Normalizing HIBP breach data:")
    if "error" in raw_data:
        return {"error": raw_data["error"]}
    breaches = raw_data.get("breaches", [])
    known_breaches = []
    
    for breach in breaches:
        breach_name = breach.get("Name")
        if breach_name:
            known_breaches.append(breach_name)
    known_breaches.sort()
    
    return \
    {
        "provider": "HaveIBeenPwned",
        "pwned_accounts_count": len(known_breaches),
        "known_breaches": known_breaches
    }

#analyze breaches for potential risks
def generate_findings_and_assets(normalized_data: dict) -> tuple:
    findings = []
    assets = []
    
    if "error" in normalized_data:
        return findings, assets
        
    pwned_count = normalized_data.get("pwned_accounts_count", 0)
    known_breaches = normalized_data.get("known_breaches", [])
    
    # If the domain has been in any breaches, generate a High severity
    #  finding(might be replaced by ai recomendations at a later date)
    if pwned_count > 0:
        findings.append(
        {
            "source": "hibp",
            "severity": "high",
            "title": f"Domain Identified in {pwned_count} Historical Data Breaches",
            "description": ("The target domain was found in known third-party data breaches. "
            "Associated email addresses and potentially passwords may be compromised."),
            "recommendation": ("Enforce strict password resets and multi-factor authentication "
            "(MFA) across the organization."),
            "evidence": {"breaches": known_breaches}
        })
            
    return findings, assets


#execution
@shared_task(name="scan.hibp")
def run_hibp(domain: str) -> dict:
    raw_data = collect_raw_data(domain)
    normalized = normalize_data(raw_data)
    findings, assets = generate_findings_and_assets(normalized)
    
    return \
    {
        "source_name": "hibp",
        "status": "completed" if "error" not in normalized else "failed",
        "raw_result": normalized,
        "findings": findings,
        "assets": assets
    }