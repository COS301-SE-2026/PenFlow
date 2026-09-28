import logging
from ipaddress import ip_address
from typing import Any

import dns.exception
import dns.resolver

logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]


def resolve_target_ips(domain: str) -> JSONDict:
    """
    Resolves the current IPv4 and IPv6 addresses for a verified domain.

    Gives us Live IPV4 and IPV6 we can use
    """

    logger.info(f"[Target Resolution] Resolving live IP address's for the domain: {domain}")

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
            f"[Target Resolution] Found {len(result['ipv4'])} "
            f"IPv4 address's for the domain: {domain}"
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
            f"[Target Resolution] Found {len(result['ipv6'])} "
            f"IPv6 address's for the domain: {domain}"
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


def resolve_target_scope(
        hostnames: list[str],
        max_ipv4_per_hostname: int = 2,
        max_ipv6_per_hostname: int = 2,
        max_unique_ips: int = 24,
) -> JSONDict:
    targets: list[JSONDict] = []
    ip_to_hostnames: dict[str, list[str]] = {}

    for hostname in hostnames:
        resolved = resolve_target_ips(hostname)

        accepted_ipv4: list[str] = []
        accepted_ipv6: list[str] = []

        for version, addresses, limit, accepted in (
            (4, resolved["ipv4"], max_ipv4_per_hostname, accepted_ipv4),
            (6, resolved["ipv6"], max_ipv6_per_hostname, accepted_ipv6),
        ):
            for value in addresses:
                try:
                    parsed_address = ip_address(value)

                except ValueError:
                    logger.warning(
                        "[Target Resolution] Ignoring invalid address %s for %s",
                        value,
                        hostname,
                    )
                    continue

                if parsed_address.version != version or not parsed_address.is_global:
                    logger.warning(
                        "[Target Resolution] Ignoring non-public address %s for %s",
                        value,
                        hostname,
                    )
                    continue

                address = str(parsed_address)

                if address in accepted:
                    continue

                if (
                    address not in ip_to_hostnames
                    and len(ip_to_hostnames) >= max_unique_ips
                ):
                    continue

                ip_to_hostnames.setdefault(address, [])
                if hostname not in ip_to_hostnames[address]:
                    ip_to_hostnames[address].append(hostname)

                accepted.append(address)

                if len(accepted) >= limit:
                    break

        targets.append(
            {
                "hostname": hostname,
                "ipv4": accepted_ipv4,
                "ipv6": accepted_ipv6,
            }
        )

    return {
        "targets": targets,
        "ip_to_hostnames": ip_to_hostnames,
    }