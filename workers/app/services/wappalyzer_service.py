import logging
import os
import logging
import warnings
import json
from pathlib import Path  
from Wappalyzer import Wappalyzer, WebPage

warnings.filterwarnings("ignore")
#Logger to tell us this file was in error
logger = logging.getLogger(__name__)

SCAN_MODE = os.getenv("SCAN_MODE", "MOCK").upper()
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
    logger.info(f"[Wappalyzer] Running in FULL LIVE mode for {domain} (local engine)")
    
    try:
        wappalyzer = Wappalyzer.latest()
        page = WebPage.new_from_url(f"https://{domain}")
        rawData = wappalyzer.analyze_with_versions_and_categories(page)
        return rawData
    except Exception as e:
        logger.error(f"X Local Wappalyzer Engine Error: {e}")
        return {"error": "Local Analysis Failed"}

def normalize_data(rawData: dict) -> dict:
    """
    Flatten and normalize Wappalyzer's output into our unified schema format.
    """
    logger.info("Normalizing Wappalyzer data:")

    if "error" in rawData:
        return {"error": rawData["error"]}
    
    cms = []
    frameworks = []
    webServers = []
    paas = []
    programmingLanguages = []
    databases = []
    cdns = []

    for techName, details in rawData.items():
        #extract first version if it exists
        versions = details.get("versions", [])
        version = versions[0] if versions else "Unknown"

        techObj = \
        {
            "name": techName,
            "version": version
        }

        # Categories come directly as a list of strings
        categories = details.get("categories", [])
        
        # Sort the technology into our unified schema categories
        for category in categories:
            if "CMS" in category:
                if techObj not in cms:
                    cms.append(techObj)
            elif "Web frameworks" in category or "JavaScript frameworks" in category or "JavaScript libraries" in category:
                if techObj not in frameworks:
                    frameworks.append(techObj)
            elif "Web servers" in category or "Reverse proxies" in category:
                if techObj not in webServers:
                    webServers.append(techObj)
            elif "PaaS" in category:
                if techObj not in paas:
                    paas.append(techObj)
            elif "Programming languages" in category:
                if techObj not in programmingLanguages:
                    programmingLanguages.append(techObj)
            elif "Databases" in category:
                if techObj not in databases:
                    databases.append(techObj)
            elif "CDN" in category:
                if techObj not in cdns:
                    cdns.append(techObj)

    return \
    {
        "provider": "Wappalyzer",
        "cms": cms,
        "frameworks": frameworks,
        "webServers": webServers,
        "paas": paas,
        "programmingLanguages": programmingLanguages,
        "databases": databases,
        "cdn": cdns
    }

#analyze tech stack for known risky software targets
def generate_findings_and_assets(normalizedData: dict) -> tuple:
    findings = []
    assets = []
    
    if "error" in normalizedData:
        return findings, assets
        
    #dictionary of tech that needs strict managment to avoid common exploits here
    RISKY_TECH = \
    {
        "PHP": "Ensure PHP versions are 8.0+. Older versions are highly vulnerable.",
        "WordPress": "WordPress is prone to plugin vulnerabilities. Ensure strict update policies.",
        "jQuery": "Older jQuery versions have known XSS vulnerabilities."
    }
    
    categoriesToCheck = \
    [
        "cms", "frameworks", "webServers", "paas", 
        "programmingLanguages", "databases", "cdn"
    ]

    for categoryKey in categoriesToCheck:
        for tech in normalizedData.get(categoryKey, []):
            techName = tech.get("name")
            
            if techName in RISKY_TECH:
                findings.append(
                {
                    "source": "wappalyzer",
                    "severity": "info",
                    "title": f"Commonly Targeted Technology Detected: {techName}",
                    "description": f"The target is using {techName}, which requires strict patch management.",
                    "recommendation": RISKY_TECH[techName],
                    "evidence": {"technology": techName, "version": tech.get("version")}
                })
            
    return findings, assets

#execution
def run_wappalyzer(domain: str) -> dict:
    rawData = collect_raw_data(domain)
    normalized = normalize_data(rawData)
    findings, assets = generate_findings_and_assets(normalized)
    
    return \
    {
        "source_name": "wappalyzer",
        "status": "completed" if "error" not in normalized else "failed",
        "raw_result": {"tech_stack": normalized},
        "findings": findings,
        "assets": assets
    }