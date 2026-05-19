import os
import json
import logging
from pathlib import Path
import dns.resolver
import whois

logger = logging.getLogger(__name__)

SCAN_MODE = os.getenv("SCAN_MODE", "MOCK").upper()
WORKERS_ROOT = Path(__file__).resolve().parent.parent.parent

#collect raw data from mocks or live mode
def collect_raw_data(domain: str) -> dict:
    """Collects DNS records and WHOIS data (Mock or Live)."""
    
    if SCAN_MODE == "MOCK":
        logger.info(f"[DNS/WHOIS] Running in MOCK mode for {domain}")
        mockFile = WORKERS_ROOT / "docs" / "raw_samples" / "DnsWhois_Response.json"
        try:
            with open(mockFile, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("X Mock file not found.")
            return {}

    #Live Mode (no key required for DNS and WHOIS)
    logger.info(f"[DNS/WHOIS] Running in FULL LIVE mode for {domain}")
    
    rawData = {"dns": {"mx": [], "txt": []}, "whois": {}}
    
    #Fetch DNS Records
    try:
        mx_answers = dns.resolver.resolve(domain, 'MX')
        rawData["dns"]["mx"] = [str(rdata) for rdata in mx_answers]
    except Exception:
        pass # No MX records found
        
    try:
        txt_answers = dns.resolver.resolve(domain, 'TXT')
        rawData["dns"]["txt"] = [str(rdata) for rdata in txt_answers]
    except Exception:
        pass # No TXT records found
        
    # Fetch WHOIS Data
    try:
        w = whois.whois(domain)
        rawData["whois"] = \
        {
            "registrar": w.registrar,
            "creation_date": str(w.creation_date[0]) if isinstance(w.creation_date, list) else str(w.creation_date),
            "expiration_date": str(w.expiration_date[0]) if isinstance(w.expiration_date, list) else str(w.expiration_date),
            "name_servers": w.name_servers
        }
    except Exception as e:
        logger.error(f"X WHOIS Error: {e}")
        
    return rawData