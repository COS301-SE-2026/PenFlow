import logging

# Logger to track this specific worker
logger = logging.getLogger(__name__)

def normalize_crtsh_data(raw_data: list) -> dict:
    """
    Extracts and normalizes subdomains from raw crt.sh JSON.
    Removes all duplicates.
    """
    logger.info("Normalizing crt.sh data:")
    
    #SET doesnt allow duplicates, so we can just add all the subdomains and we will inherintly have a unique list of subdomains at the end.
    uniqueSubdomains = set()

    for entry in raw_data:
        # Safe extraction of the domain string
        nameValue = entry.get("name_value", "")
        
        if not nameValue:
            continue

        # crt.sh frequently crams multiple subdomains into one string separated by a newline
        splitNames = nameValue.split("\n")
        
        for name in splitNames:
            # Clean up any accidental whitespace
            cleanName = name.strip()
            
            # take away the "wildcard cert" it is a pre domain addition stating that something can be infront of the domain. It is not useful for us and it is not a real subdomain so we will remove it.
            if cleanName.startswith("*."):
                cleanName = cleanName[2:]
                
            # Add the cleaned domain to our set
            if cleanName:
                uniqueSubdomains.add(cleanName)

    # Convert the set back to a sorted list so the JSON output is consistent and readable
    discoveredNames = sorted(list(uniqueSubdomains))
    
    # Our strict data contract schema format for the subdomains section
    final_result = \
    {
        "provider": "crt.sh",
        "total_found": len(discoveredNames),
        "discovered_names": discoveredNames
    }

    return final_result