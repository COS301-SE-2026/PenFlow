import logging
import httpx

logger = logging.getLogger(__name__)

RDAP_BOOTSTRAP_URL = "https://rdap.org/domain/{domain}"


def collect_whois_raw_data(domain: str) -> dict:
    """
    Collects raw WHOIS/RDAP registration data for a domain, used before normalization.
    """
    logger.info("Collecting WHOIS/RDAP data for domain: %s", domain)

    try:
        response = httpx.get(
            RDAP_BOOTSTRAP_URL.format(domain=domain),
            timeout=10,
            follow_redirects=True,
        )

        response.raise_for_status()

        return {
            "domain": domain,
            "provider": "RDAP",
            "raw_response": response.json(),
        }

    except Exception as error:
        return {
            "domain": domain,
            "provider": "RDAP",
            "error": str(error),
            "raw_response": {},
        }