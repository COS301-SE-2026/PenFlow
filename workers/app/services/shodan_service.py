#lets us convert string IP addr to a int for faster db indexing.
import ipaddress
import logging

#Logger to tell us this file was in error
logger = logging.getLogger(__name__)

def normalize_shodan_data(raw_data: dict) -> dict:
    """
    Extracts and normalizes data from raw Shodan JSON.
    Returns a dictionary matching the PenFlow Data Contract Schema.
    """
    logger.info("Normalizing Shodan data:")

    #use get so that if the fields are null or in error we return "Unkown" instead of erroring out the entire process.
    hosting_provider = raw_data.get("org", "Unknown")
    ipStr = raw_data.get("ip_str", "Unknown")

    #Convert th Ip dtring(192.168.1.1) int a faster to process ip intger.(9999999999). This is faster to query and index whihc will help us in giving a speedy response to the user.
    ipInt = 0
    try:
        if ipStr != "Unknown":
            ipInt = int(ipaddress.IPv4Address(ipStr))
    except (ValueError, ipaddress.AddressValueError):
        logger.warning(f"Failed to convert IP string to int: {ipStr}")

    #convert raw pport form to a list of ports that are open.
    raw_ports = raw_data.get("ports", [])
    formatted_ports = []
    
    for p in raw_ports:
        port_object = \
        {
            "port": p,
            "state": "open"
        }
        formatted_ports.append(port_object)

    #our strict fata contract schema format for the shodan section
    final_result = \
    {
        "provider": "Shodan",
        "hosting_provider": hosting_provider,
        "ip_details": 
        [
            {
                "ip_str": ipStr,
                "ip_int": ipInt
            }
        ],
        "open_ports": formatted_ports
    }
    
    return final_result