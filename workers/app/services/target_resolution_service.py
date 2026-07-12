from typing import Any
import logging
import dns.exception
import dns.resolver
logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]


def resolve_target_ips(domain: str) -> JSONDict:
    """
    Resolves the current IPv4 and IPv6 addresses for a verified domain.

    Gives us Live IPV4 and IPV6 we can use
    """

    logger.info(
        f"[Target Resolution] Resolving live IP address's for the domain: {domain}"
    )

    result = {
        "ipv4": [],
        "ipv6": [],
    }

    resolver = dns.resolver.Resolver()
    resolver.timeout = 5.0
    resolver.lifetime = 5.0

    # IPv4
    try:
        records = resolver.resolve(domain, "A")
        result["ipv4"] = [record.to_text() for record in records]

        logger.info(
            f"[Target Resolution] Found {len(result['ipv4'])} IPv4 address's for the domain: {domain}"
        )

    except (
        dns.resolver.NXDOMAIN,
        dns.resolver.NoAnswer,
        dns.resolver.NoNameservers,
        dns.exception.Timeout,
    ) as error:
        logger.warning(
            f"[Target Resolution] Unable to resolve IPv4 for the domain: {domain} ({error})"
        )

    # IPv6
    try:
        records = resolver.resolve(domain, "AAAA")
        result["ipv6"] = [record.to_text() for record in records]

        logger.info(
            f"[Target Resolution] Found {len(result['ipv6'])} IPv6 address's for the domain: {domain}"
        )

    except (
        dns.resolver.NXDOMAIN,
        dns.resolver.NoAnswer,
        dns.resolver.NoNameservers,
        dns.exception.Timeout,
    ) as error:
        logger.warning(
            f"[Target Resolution] Unable to resolve IPv6 for the domain: {domain} ({error})"
        )

    return result