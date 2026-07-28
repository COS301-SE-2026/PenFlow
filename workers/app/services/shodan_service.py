# lets us convert string IP addr to a int for faster db indexing.
import ipaddress
import json
import logging
import os
import socket
from pathlib import Path
import ipaddress
import httpx

# Logger to tell us this file was in error
logger = logging.getLogger(__name__)

SCAN_MODE = os.getenv("SCAN_MODE", "MOCK").upper()
SHODAN_API_KEY = os.getenv("SHODAN_API_KEY", "fake_key_1234")
WORKERS_ROOT = Path(__file__).resolve().parent.parent.parent


# collect raw data from mocks or from shodan depending on mode
def collect_raw_data(domain: str) -> dict:
    """Collects infrastructure data from Shodan (Mock or Live)."""

    # Mock mode
    if SCAN_MODE == "MOCK" or not SHODAN_API_KEY or "fake" in SHODAN_API_KEY.lower():
        logger.info(f"[Shodan] Running in MOCK mode for {domain}")
        safe_domain = domain.replace(".", "_")
        mock_file = WORKERS_ROOT / "docs" / "raw_samples" / f"Shodan_{safe_domain}.json"

        if not mock_file.exists():
            mock_file = WORKERS_ROOT / "docs" / "raw_samples" / "Shodan_Response.json"

        try:
            with open(mock_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.exception("X Mock file not found. Returning empty dict.")
            return {}

    # Live Mode
    logger.info(f"[Shodan] Running in FULL LIVE mode for {domain}")
    if not SHODAN_API_KEY or SHODAN_API_KEY == "fake_key_1234":
        logger.exception("X LIVE mode requires a valid SHODAN_API_KEY in the .env file!")
        return {"error": "Missing Shodan API Key"}

    # test if input is ip or domain(we need in ip format for shodan)
    target_ip = None
    try:
        ip_obj = ipaddress.ip_address(domain)
        target_ip = str(ip_obj)
        logger.info(f"[Shodan] Input is already a valid IP: {target_ip}")
    except ValueError:
        # resolve domain to ip
        try:
            target_ip = socket.gethostbyname(domain)
            logger.info(f"[Shodan] Resolved domain {domain} to IP {target_ip}")
        except socket.gaierror:
            logger.exception(f"X Failed to resolve IP for domain: {domain}")
            return {"error": "DNS Resolution Failed"}

    # secuirity check
    if ipaddress.ip_address(target_ip).is_private:
        logger.error(f"X Security Block: Attempted to scan a private/internal IP ({target_ip})")
        return {"error": "Private IP Scan Blocked"}

    # Query shodan
    url = f"https://api.shodan.io/shodan/host/{target_ip}?key={SHODAN_API_KEY}"

    with httpx.Client() as client:
        try:
            res = client.get(url, timeout=15.0)
            if res.status_code == 404:
                logger.info(f"[Shodan] No infrastructure data found on Shodan for {target_ip}")
                return {"ip_str": target_ip, "ports": [], "org": "Unknown"}
            res.raise_for_status()
            return res.json()
        except httpx.HTTPError as e:
            logger.exception(f"X Shodan API Error: {e}")
            return {"error": "API Request Failed"}


def normalize_data(raw_data: dict) -> dict:
    """
    Flattens either the Mock JSON or the massive Live JSON into our contract
    """
    if "error" in raw_data:
        return {"error": raw_data["error"]}

    # convert raw port form to a list of ports that are open.
    raw_ports = raw_data.get("ports", [])
    open_ports = [{"port": p, "state": "open"} for p in raw_ports]

    ip_str = raw_data.get("ip_str", "Unknown")
    ip_addresses = [{"ip_str": ip_str}] if ip_str != "Unknown" else []

    return {
        "hosting_provider": raw_data.get("org", raw_data.get("isp", "Unknown")),
        "ip_addresses": ip_addresses,
        "open_ports": open_ports,
    }


def generate_findings_and_assets(normalized_data: dict) -> tuple:
    """Analyzes open ports for risks and extracts discovered assets."""
    findings = []
    assets = []

    if "error" in normalized_data:
        return findings, assets

    # Add the IP address to the PenFlow Asset inventory
    for ip_obj in normalized_data.get("ip_addresses", []):
        ip_str = ip_obj["ip_str"]
        ip_version = ipaddress.ip_address(ip_str).version
        assets.append(
        {
            "asset_type": "ipv4" if ip_version == 4 else "ipv6",
            "identifier": ip_str,
            "asset_metadata": {
                "source": "shodan",
            },
        })

    # Risky port definitions
    RISKY_PORTS = {
        21: {"service": "FTP", "severity": "medium"},
        22: {"service": "SSH", "severity": "info"},
        23: {"service": "Telnet", "severity": "high"},
        3306: {"service": "MySQL", "severity": "medium"},
        3389: {"service": "RDP", "severity": "high"},
        445: {"service": "SMB", "severity": "high"},
    }

    # Analyze exposed ports
    for port_data in normalized_data.get("open_ports", []):
        port_num = port_data.get("port")
        if port_num in RISKY_PORTS:
            risk = RISKY_PORTS[port_num]
            findings.append(
                {
                    "source": "shodan",
                    "severity": risk["severity"],
                    "title": f"Exposed {risk['service']} Service (Port {port_num})",
                    "description": (
                        f"The target is exposing port {port_num}"
                        f" ({risk['service']}) to the public internet."
                    ),
                    "recommendation": (
                        f"Restrict access to port {port_num} "
                        f"using a firewall or VPN. It should not be publicly accessible."
                    ),
                    "evidence": {"port": port_num, "state": port_data.get("state")},
                }
            )

    return findings, assets
