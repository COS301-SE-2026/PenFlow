import logging

#Logger to tell us this file was in error
logger = logging.getLogger(__name__)

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