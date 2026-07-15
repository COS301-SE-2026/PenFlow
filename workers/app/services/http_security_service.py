from typing import Any
import logging
import requests

logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]

def run_http_security_scan\
(
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
        "targets": [],
    }

    for port in ports:

        service = port.get("service")

        if service not in \
        [
            "http",
            "https",
        ]:
            continue

        protocol = \
        (
            "https"
            if service == "https"
            else "http"
        )

        url = \
        (
            f"{protocol}://{ip_address}:{port['port']}"
        )

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