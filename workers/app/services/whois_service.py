import logging
from typing import Any

import httpx

JSONDict = dict[str, Any]

logger = logging.getLogger(__name__)

RDAP_BOOTSTRAP_URL = "https://rdap.org/domain/{domain}"


def collect_whois_raw_data(domain: str) -> JSONDict:
    """
    Collects raw WHOIS/RDAP registration data for a domain, used before normalization.
    """
    logger.info("Collecting WHOIS/RDAP data for domain: %s", domain)

    timeout = httpx.Timeout(
        10.0,
        connect=5.0,
    )

    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
        ) as client:

            response = client.get(
                RDAP_BOOTSTRAP_URL.format(domain=domain),
            )

            response.raise_for_status()

            return {
                "domain": domain,
                "provider": "RDAP",
                "status_code": response.status_code,
                "lookup_url": str(response.url),
                "raw_response": response.json(),
            }

    except httpx.HTTPStatusError as error:
        logger.warning(
            "RDAP HTTP failure for %s: %s",
            domain,
            error.response.status_code,
        )

        return {
            "domain": domain,
            "provider": "RDAP",
            "error": f"HTTP {error.response.status_code}",
            "raw_response": {},
        }

    except httpx.RequestError as error:
        logger.warning(
            "RDAP request error for %s: %s",
            domain,
            error,
        )

        return {
            "domain": domain,
            "provider": "RDAP",
            "error": str(error),
            "raw_response": {},
        }