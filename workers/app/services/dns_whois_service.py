import os
import json
import logging
from pathlib import Path
from celery import shared_task
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

#normalize data to fit our strict PDF contract
def normalize_data(rawData: dict) -> dict:
    if "error" in rawData:
        return {"error": rawData["error"]}

    dnsData = rawData.get("dns", {})
    whoisData = rawData.get("whois", {})
    
    records = []
    detectedServices = set()

    # Process MX
    if dnsData.get("mx"):
        records.append({"record_type": "MX", "status": "Pass", "finding": "MX records are configured."})
        if "google" in str(dnsData.get("mx")).lower(): detectedServices.add("Google Workspace")
    else:
        records.append({"record_type": "MX", "status": "Fail", "finding": "No MX records found."})

    # Process SPF / DMARC from TXT
    txtList = dnsData.get("txt", [])
    txt_records = " ".join(txtList).lower()
    
    if "v=spf1" in txt_records:
        records.append({"record_type": "SPF", "status": "Pass", "finding": "SPF record is present."})
    else:
        records.append({"record_type": "SPF", "status": "Fail", "finding": "No SPF record found. Vulnerable to spoofing."})
        
    if "v=dmarc1" in txt_records:
        records.append({"record_type": "DMARC", "status": "Pass", "finding": "DMARC record is present."})
    else:
        records.append({"record_type": "DMARC", "status": "Fail", "finding": "No DMARC record found. Email spoofing possible."})

    # Detect third-party services from TXT recordsprimary ones we care for)
    for txt in txtList:
        txt_lower = txt.lower()
        if "adobe" in txt_lower: detectedServices.add("Adobe")
        if "anthropic" in txt_lower: detectedServices.add("Anthropic")
        if "apple" in txt_lower: detectedServices.add("Apple")
        if "atlassian" in txt_lower: detectedServices.add("Atlassian")
        if "box" in txt_lower: detectedServices.add("Box")
        if "canva" in txt_lower: detectedServices.add("Canva")
        if "citrix" in txt_lower: detectedServices.add("Citrix")
        if "docusign" in txt_lower: detectedServices.add("DocuSign")
        if "drift" in txt_lower: detectedServices.add("Drift")
        if "facebook" in txt_lower: detectedServices.add("Facebook")
        if "google-site-verification" in txt_lower: detectedServices.add("Google")
        if "jetbrains" in txt_lower: detectedServices.add("JetBrains")
        if "monday" in txt_lower: detectedServices.add("Monday.com")
        if "openai" in txt_lower: detectedServices.add("OpenAI")
        if "slack" in txt_lower: detectedServices.add("Slack")
        if "stripe" in txt_lower: detectedServices.add("Stripe")
        if "zoom" in txt_lower: detectedServices.add("Zoom")

    return \
    {
        "domain_security": 
        {
            "provider": "Native Python",
            "records": records,
            "whois": whoisData,
            "detected_services": sorted(list(detectedServices))
        }
    }

#analyze DNS records for spoofing risks
def generate_findings_and_assets(normalizedData: dict) -> tuple:
    findings = []
    assets = []
    
    if "error" in normalizedData:
        return findings, assets
        
    domainSecurity = normalizedData.get("domain_security", {})
    records = domainSecurity.get("records", [])
    
    # Check for missing email security records
    for record in records:
        if record.get("status") == "Fail" and record.get("record_type") in ["SPF", "DMARC"]:
            findings.append(
            {
                "source": "dns_whois",
                "severity": "medium",
                "title": f"Missing {record.get('record_type')} Record",
                "description": record.get("finding"),
                "recommendation": f"Configure a valid {record.get('record_type')} TXT record to prevent unauthorized email spoofing from this domain.",
                "evidence": {"record_type": record.get("record_type")}
            })
            
    return findings, assets


#execution
@shared_task(name="scan.dns_whois")
def run_dns_whois(domain: str) -> dict:
    rawData = collect_raw_data(domain)
    normalized = normalize_data(rawData)
    findings, assets = generate_findings_and_assets(normalized)
    
    return \
    {
        "source_name": "dns",
        "status": "completed" if "error" not in normalized else "failed",
        "raw_result": normalized,
        "findings": findings,
        "assets": assets
    }    