from typing import Any
import logging

import nmap

logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]

SCAN_PROFILES = \
{
    "standard":
    (
        "-Pn "
        "-sV "
        "--top-ports 1000 "
        "--script=http-title,http-headers,ssl-cert,banner"
    ),
    #can add more profiles here later on
}


def run_live_nmap_scan\
(
    ip_address: str,
    profile: str,
) -> JSONDict:
    """
    Runs Nmap scan on the ip address's we gained from the target resolution worker

    Standard profile should return:
    host status
    Open TCP ports
    Running services
    Service versions
    HTTP metadata
    SSL/TLS certificate information
    Safe NSE script output

    Plan for future profiles like full and advanced if we have time
    """

    (logger.info
    (
        f"[NMAP_Service] Starting '{profile}' scan for IP address: {ip_address}"
    ))

    scan_args = SCAN_PROFILES.get(profile)

    #must provide a profile (for now we are only using standard scan)
    if scan_args is None:
        raise (ValueError
        (
            f"Unsupported scan profile: {profile}"
        ))

    if ":" in ip_address:
        scan_args += " -6"
    scanner = nmap.PortScanner()

    result: JSONDict = \
    {
        "ip": ip_address,
        "profile": profile,
        "status": "down",
        "hostnames": [],
        "ports": [],
    }

    try:

        scanner.scan(
            hosts=ip_address,
            arguments=scan_args,
        )

        if not scanner.all_hosts():
            (logger.warning
            (
                f"[NMAP_Service] No response received from target: {ip_address}"
            ))
            return result

        host = scanner.all_hosts()[0]
        host_data = scanner[host]

        result["status"] = host_data.state()

        if "hostnames" in host_data:
            result["hostnames"] = \
            [
                hostname.get("name")
                for hostname in host_data["hostnames"]
                if hostname.get("name")
            ]

        if "tcp" in host_data:

            for port_number, port_data in host_data["tcp"].items():

                if port_data.get("state") != "open":
                    continue

                scripts = port_data.get(
                    "script",
                    {},
                )

                parsed_port = {
                    "port": port_number,
                    "protocol": "tcp",
                    "state": "open",
                    "service": port_data.get
                    (
                        "name",
                        "unknown",
                    ),
                    "product": port_data.get
                    (
                        "product",
                        "",
                    ),
                    "version": port_data.get
                    (
                        "version",
                        "",
                    ),
                    "extra_info": port_data.get
                    (
                        "extra_info",
                        "",
                    ),

                    "http_title": scripts.get
                    (
                        "http-title",
                        "",
                    ),

                    "http_headers": scripts.get
                    (
                        "http-headers",
                        "",
                    ),

                    "server_header": scripts.get
                    (
                        "http-server-header",
                        "",
                    ),

                    "ssl_certificate": scripts.get
                    (
                        "ssl-cert",
                        "",
                    ),

                    "banner": scripts.get
                    (
                        "banner",
                        "",
                    ),

                    "scripts": scripts,
                }

                result["ports"].append(parsed_port)

        logger.info(
            f"[NMAP_Service] Completed scan for {ip_address}. "
            f"Found {len(result['ports'])} open TCP ports."
        )

        return result

    except nmap.PortScannerError as error:
        logger.exception(
            f"[NMAP_Service] PortScanner error while scanning "
            f"{ip_address}: {error}"
        )
        raise

    except Exception as error:
        logger.exception(
            f"[NMAP_Service] Unexpected error while scanning "
            f"{ip_address}: {error}"
        )
        raise