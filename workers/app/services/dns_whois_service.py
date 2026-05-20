import json
import logging
import os
from pathlib import Path

import dns.resolver
import whois
from celery import shared_task

logger = logging.getLogger(__name__)

SCAN_MODE = os.getenv("SCAN_MODE", "MOCK").upper()
WORKERS_ROOT = Path(__file__).resolve().parent.parent.parent

#collect raw data from mocks or live mode
def collect_raw_data(domain: str) -> dict:
    """Collects DNS records and WHOIS data (Mock or Live)."""
    
    if SCAN_MODE == "MOCK":
        logger.info(f"[DNS/WHOIS] Running in MOCK mode for {domain}")
        mock_file = WORKERS_ROOT / "docs" / "raw_samples" / "DnsWhois_Response.json"
        try:
            with open(mock_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("X Mock file not found.")
            return {}

    #Live Mode (no key required for DNS and WHOIS)
    logger.info(f"[DNS/WHOIS] Running in FULL LIVE mode for {domain}")
    
    raw_data = {"dns": {"mx": [], "txt": []}, "whois": {}}
    
    #Fetch DNS Records
    try:
        mx_answers = dns.resolver.resolve(domain, 'MX')
        raw_data["dns"]["mx"] = [str(rdata) for rdata in mx_answers]
    except Exception:
        pass # No MX records found
        
    try:
        txt_answers = dns.resolver.resolve(domain, 'TXT')
        raw_data["dns"]["txt"] = [str(rdata) for rdata in txt_answers]
    except Exception:
        pass # No TXT records found
        
    # Fetch WHOIS Data
    try:
        w = whois.whois(domain)

        c_date = w.creation_date[0] if isinstance(w.creation_date, list) else w.creation_date
        e_date = w.expiration_date[0] if isinstance(w.expiration_date, list) else w.expiration_date
        raw_data["whois"] = \
        {
            "registrar": w.registrar,
            "creation_date": str(c_date),
            "expiration_date": str(e_date),
            "name_servers": w.name_servers
        }
    except Exception as e:
        logger.exception(f"X WHOIS Error: {e}")
        
    return raw_data

#normalize data to fit our strict PDF contract
def normalize_data(raw_data: dict) -> dict:
    if "error" in raw_data:
        return {"error": raw_data["error"]}

    dns_data = raw_data.get("dns", {})
    whois_data = raw_data.get("whois", {})
    
    records = []
    detected_services = set()

    # Process MX
    if dns_data.get("mx"):
        records.append({
            "record_type": "MX",
            "status": "Pass",
            "finding": "MX records are configured."
        })
        if "google" in str(dns_data .get("mx")).lower(): 
            detected_services.add("Google Workspace")
    else:
        records.append({
            "record_type": "MX",
            "status": "Fail",
            "finding": "No MX records found."
        })

    # Process SPF / DMARC from TXT
    txt_list = dns_data.get("txt", [])
    txt_records = " ".join(txt_list).lower()
    
    if "v=spf1" in txt_records:
        records.append({
            "record_type": "SPF",
            "status": "Pass",
            "finding": "SPF record is present."
        })
    else:
        records.append({
            "record_type": "SPF",
            "status": "Fail",
            "finding": "No SPF record found. Vulnerable to spoofing."
        })

    if "v=dmarc1" in txt_records:
        records.append({
            "record_type": "DMARC",
            "status": "Pass",
            "finding": "DMARC record is present."
        })
    else:
        records.append({
            "record_type": "DMARC",
            "status": "Fail",
            "finding": "No DMARC record found. Email spoofing possible."
        })

    services_mapping ={
        "adobe": "Adobe",
        "anthropic": "Anthropic",
        "apple": "Apple",
        "atlassian": "Atlassian",
        "box": "Box",
        "canva": "Canva",
        "citrix": "Citrix",
        "docusign": "DocuSign",
        "drift": "Drift",
        "facebook": "Facebook",
        "google-site-verification": "Google",
        "jetbrains": "JetBrains",
        "monday": "Monday.com",
        "openai": "OpenAI",
        "slack": "Slack",
        "stripe": "Stripe",
        "zoom": "Zoom"
    }
    # Detect third-party services from TXT records (primary ones we care for)
    for txt in txt_list:
        txt_lower = txt.lower()
        for keyword, service_name in services_mapping.items():
            if keyword in txt_lower:
                detected_services.add(service_name)

    return \
    {
        "domain_security": 
        {
            "provider": "Native Python",
            "records": records,
            "whois": whois_data,
            "detected_services": sorted(detected_services)
        }
    }

#analyze DNS records for spoofing risks
def generate_findings_and_assets(normalized_data: dict) -> tuple:
    findings = []
    assets = []
    
    if "error" in normalized_data:
        return findings, assets
        
    domain_security = normalized_data.get("domain_security", {})
    records = domain_security.get("records", [])
    
    # Check for missing email security records
    for record in records:
        if record.get("status") == "Fail" and record.get("record_type") in ["SPF", "DMARC"]:
            rec_type = record.get("record_type")

            rec_text = (
                f"Configure a valid {rec_type} TXT record to "
                "prevent unauthorized email spoofing from this domain."
            )
            findings.append(
            {
                "source": "dns_whois",
                "severity": "medium",
                "title": f"Missing {rec_type} Record",
                "description": record.get("finding"),
                "recommendation": rec_text,
                "evidence": {"record_type": rec_type}
            })
            
    return findings, assets


#execution
@shared_task(name="scan.dns_whois")
def run_dns_whois(domain: str) -> dict:
    raw_data = collect_raw_data(domain)
    normalized = normalize_data(raw_data)
    findings, assets = generate_findings_and_assets(normalized)
    
    return \
    {
        "source_name": "dns",
        "status": "completed" if "error" not in normalized else "failed",
        "raw_result": normalized,
        "findings": findings,
        "assets": assets
    }    