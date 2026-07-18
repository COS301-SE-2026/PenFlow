import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]
#specifically known https ports
HTTPS_PORTS = [
    443,
    8443,
    9443,
    10443,
]

def run_http_security_scan\
(
    hostname: str,
    ip_address: str,
    ports: list[JSONDict],
    timeout: int = 5,
) -> JSONDict:
    """
    Does HTTP security check on the services/ports that nmap uncovered

    Returns:
    HTTP status
    Response headers
    Security header values
    """

    (logger.info
    (
        f"[HTTP_Service] Starting HTTP security scan against the ip address:  {ip_address}"
    ))

    result: JSONDict = \
    {
        "ip": ip_address,
        "hostname": hostname,
        "targets": [],
    }

    for port in ports:

        service = (
                port.get("service") or ""
        ).lower()

        #For this worker we only care about http relation
        if (
                port["port"] not in HTTPS_PORTS
                and "http" not in service
        ):
            continue

        #http vs https
        protocol = "https" if (
                port["port"] in HTTPS_PORTS
                or "https" in service
                or "ssl" in service
                or "tls" in service
        )else "http"
        # USE HOSTNAME
        port_suffix = f":{port['port']}" if port["port"] not in (80, 443) else ""
        url = f"{protocol}://{hostname}{port_suffix}"

        try:

            response = requests.get\
            (
                url,
                timeout=timeout,
                verify=False,
                allow_redirects=True,
            )

        except requests.RequestException as error:

            (logger.warning
            (
                f"[HTTP_Service] Failed to connect to {url}: {error}"
            ))

            continue

        headers = response.headers

        parsed_target = \
        {
            "url": url,
            "port": port["port"],
            "protocol": protocol,
            "status_code": response.status_code,

            "security_headers":
            {
                "strict_transport_security":
                    headers.get\
                    (
                        "Strict-Transport-Security"
                    ),

                "content_security_policy":
                    headers.get\
                    (
                        "Content-Security-Policy"
                    ),

                "content_security_policy_report_only":
                    headers.get \
                            (
                            "Content-Security-Policy-Report-Only"
                        ),

                "x_frame_options":
                    headers.get\
                    (
                        "X-Frame-Options"
                    ),

                "referrer_policy":
                    headers.get\
                    (
                        "Referrer-Policy"
                    ),

                "permissions_policy":
                    headers.get\
                    (
                        "Permissions-Policy"
                    ),

                "x_content_type_options":
                    headers.get\
                    (
                        "X-Content-Type-Options"
                    ),
            },

            "server":
                headers.get\
                (
                    "Server"
                ),

            "powered_by":
                headers.get\
                (
                    "X-Powered-By"
                ),

            "headers":
                dict(headers),
        }

        result["targets"].append(parsed_target)

    (logger.info
    (
        f"[HTTP_Service] Completed scan against the ip address: {ip_address}. "
        f"Inspected {len(result['targets'])} HTTP endpoint(s)."
    ))

    return result