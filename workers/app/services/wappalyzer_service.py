import logging
import os
import logging
import warnings
import json
from pathlib import Path  
from Wappalyzer import Wappalyzer, WebPage
from celery import shared_task

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
        safe_domain = domain.replace(".", "_")
        mock_file = WORKERS_ROOT / "docs" / "raw_samples" / f"Wappalyzer_{safe_domain}.json"
        
        if not mock_file.exists():
            mock_file = WORKERS_ROOT / "docs" / "raw_samples" / "Wappalyzer_Response.json"
            
        try:
            with open(mock_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.exception("X Mock file not found. Returning empty dict.")
            return {}

    #Live Mode
    logger.info(f"[Wappalyzer] Running in FULL LIVE mode for {domain} (local engine)")
    
    try:
        wappalyzer = Wappalyzer.latest()
        page = WebPage.new_from_url(f"https://{domain}")
        raw_data = wappalyzer.analyze_with_versions_and_categories(page)
        return raw_data
    except Exception as e:
        logger.exception(f"X Local Wappalyzer Engine Error: {e}")
        return {"error": "Local Analysis Failed"}

def normalize_data(raw_data: dict) -> dict:
    """
    Flatten and normalize Wappalyzer's output into our unified schema format.
    """
    logger.info("Normalizing Wappalyzer data:")

    if "error" in raw_data:
        return {"error": raw_data["error"]}
    normalized = {
        "provider": "Wappalyzer",
        "cms": [],
        "frameworks": [],
        "webServers": [],
        "paas": [],
        "programmingLanguages": [],
        "databases": [],
        "cdn": []
    }

    categories_mapping = {
        "CMS": "cms",
        "Web frameworks": "frameworks",
        "JavaScript frameworks": "frameworks",
        "JavaScript libraries": "frameworks",
        "Web servers": "webServers",
        "Reverse proxies": "webServers",
        "PaaS": "paas",
        "Programming languages": "programmingLanguages",
        "Databases": "databases",
        "CDN": "cdn"
    }

    for tech_name, details in raw_data.items():
        #extract first version if it exists
        versions = details.get("versions", [])
        version = versions[0] if versions else "Unknown"

        tech_obj = \
        {
            "name": tech_name,
            "version": version
        }

        # Categories come directly as a list of strings
        categories = details.get("categories", [])
        
        # Sort the technology into our unified schema categories
        for category in categories:
            for keyword,target_list in categories_mapping.items():
                if keyword in category and tech_obj not in normalized[target_list]:
                    normalized[target_list].append(tech_obj)
                    logger.info(f" - Detected {tech_name} categorized as {target_list}")
                    break

    return normalized

#analyze tech stack for known risky software targets
def generate_findings_and_assets(normalized_data: dict) -> tuple:
    findings = []
    assets = []
    
    if "error" in normalized_data:
        return findings, assets
        
    #dictionary of tech that needs strict managment to avoid common exploits here
    RISKY_TECH = \
    {
        "PHP": "Ensure PHP versions are 8.0+. Older versions are highly vulnerable.",
        "WordPress": "WordPress is prone to plugin vulnerabilities. Ensure strict update policies.",
        "jQuery": "Older jQuery versions have known XSS vulnerabilities."
    }
    
    categories_to_check = \
    [
        "cms", "frameworks", "webServers", "paas", 
        "programmingLanguages", "databases", "cdn"
    ]

    for category_key in categories_to_check:
        for tech in normalized_data.get(category_key, []):
            tech_name = tech.get("name")
            
            if tech_name in RISKY_TECH:
                findings.append(
                {
                    "source": "wappalyzer",
                    "severity": "info",
                    "title": f"Commonly Targeted Technology Detected: {tech_name}",
                    "description": f"The target is using {tech_name}, which requires strict patch management.",
                    "recommendation": RISKY_TECH[tech_name],
                    "evidence": {"technology": tech_name, "version": tech.get("version")}
                })
            
    return findings, assets

#execution
@shared_task(name="scan.wappalyzer")
def run_wappalyzer(domain: str) -> dict:
    raw_data = collect_raw_data(domain)
    normalized = normalize_data(raw_data)
    findings, assets = generate_findings_and_assets(normalized)
    
    return \
    {
        "source_name": "wappalyzer",
        "status": "completed" if "error" not in normalized else "failed",
        "raw_result": {"tech_stack": normalized},
        "findings": findings,
        "assets": assets
    }