#lets us convert string IP addr to a int for faster db indexing.
import ipaddress
import logging
import socket
import os
import json
import httpx
from pathlib import Path


#Logger to tell us this file was in error
logger = logging.getLogger(__name__)

SCAN_MODE = os.getenv("SCAN_MODE", "MOCK").upper()
SHODAN_API_KEY = os.getenv("SHODAN_API_KEY", "fake_key_1234")
WORKERS_ROOT = Path(__file__).resolve().parent.parent.parent


#collect raw data from mocks or from shodan depending on mode
def collect_raw_data(domain: str) -> dict:
    """Collects infrastructure data from Shodan (Mock or Live)."""
    
    #Mock mode
    if SCAN_MODE == "MOCK":
        logger.info(f"[Shodan] Running in MOCK mode for {domain}")
        safeDomain = domain.replace(".", "_")
        mockFile = WORKERS_ROOT / "docs" / "raw_samples" / f"Shodan_{safeDomain}.json"
        
        if not mockFile.exists():
            mockFile = WORKERS_ROOT / "docs" / "raw_samples" / "Shodan_Response.json"
            
        try:
            with open(mockFile, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("X Mock file not found. Returning empty dict.")
            return {}

    #Live Mode
    logger.info(f"[Shodan] Running in FULL LIVE mode for {domain}")
    
    if not SHODAN_API_KEY or SHODAN_API_KEY == "fake_key_1234":
        logger.error("X LIVE mode requires a valid SHODAN_API_KEY in the .env file!")
        return {"error": "Missing Shodan API Key"}

    #test if input is ip or domain(we need in ip format for shodan)
    targetIp = None
    try:
        ipObj = ipaddress.ip_address(domain)
        targetIp = str(ipObj)
        logger.info(f"[Shodan] Input is already a valid IP: {targetIp}")
    except ValueError:
        #resolve domain to ip
        try:
            targetIp = socket.gethostbyname(domain)
            logger.info(f"[Shodan] Resolved domain {domain} to IP {targetIp}")
        except socket.gaierror:
            logger.error(f"X Failed to resolve IP for domain: {domain}")
            return {"error": "DNS Resolution Failed"}

    # secuirity check
    if ipaddress.ip_address(targetIp).is_private:
        logger.error(f"X Security Block: Attempted to scan a private/internal IP ({targetIp})")
        return {"error": "Private IP Scan Blocked"}

    #Query shodan
    url = f"https://api.shodan.io/shodan/host/{targetIp}?key={SHODAN_API_KEY}"
    
    with httpx.Client() as client:
        try:
            res = client.get(url, timeout=15.0)
            if res.status_code == 404:
                logger.info(f"[Shodan] No infrastructure data found on Shodan for {targetIp}")
                return {"ipStr": targetIp, "ports": [], "org": "Unknown"}
            res.raise_for_status()
            return res.json()
        except httpx.HTTPError as e:
            logger.error(f"X Shodan API Error: {e}")
            return {"error": "API Request Failed"}



def normalize_data(rawData: dict) -> dict:
    """
    Flattens either the Mock JSON or the massive Live JSON into our contract
    """
    if "error" in rawData:
        return {"error": rawData["error"]}


    #convert raw pport form to a list of ports that are open.
    rawPorts = rawData.get("ports", [])
    openPorts=  [{"port": p, "state": "open"} for p in rawPorts]
    
    ipStr = rawData.get("ip_str", "Unknown")
    ipAddresses = [{"ip_str": ipStr}] if ipStr != "Unknown" else []

    return {
        "hosting_provider": rawData.get("org", rawData.get("isp", "Unknown")),
        "ip_addresses": ipAddresses,
        "open_ports": openPorts,
    }

def generate_findings_and_assets(normalized_data: dict) -> tuple:
    """Analyzes open ports for risks and extracts discovered assets."""
    findings = []
    assets = []
    
    if "error" in normalized_data:
        return findings, assets

    # Add the IP address to the PenFlow Asset inventory
    for ipObj in normalized_data.get("ip_addresses", []):
        assets.append(
        {
            "asset_type": "ip_address",
            "value": ipObj["ip_str"],
            "source": "shodan"
        })

    # Risky port definitions
    RISKY_PORTS = {
        21: {"service": "FTP", "severity": "medium"},
        22: {"service": "SSH", "severity": "info"},
        23: {"service": "Telnet", "severity": "high"},
        3306: {"service": "MySQL", "severity": "medium"},
        3389: {"service": "RDP", "severity": "high"},
        445: {"service": "SMB", "severity": "high"}
    }

    # Analyze exposed ports
    for portData in normalized_data.get("open_ports", []):
        portNum = portData.get("port")
        if portNum in RISKY_PORTS:
            risk = RISKY_PORTS[portNum]
            findings.append(
            {
                "source": "shodan",
                "severity": risk["severity"],
                "title": f"Exposed {risk['service']} Service (Port {portNum})",
                "description": f"The target is exposing port {portNum} ({risk['service']}) to the public internet.",
                "recommendation": f"Restrict access to port {portNum} using a firewall or VPN. It should not be publicly accessible.",
                "evidence": {"port": portNum, "state": portData.get("state")}
            })

    return findings, assets

#execution
def run_shodan(domain: str) -> dict:
    rawData = collect_raw_data(domain)
    normalized = normalize_data(rawData)
    findings, assets = generate_findings_and_assets(normalized)

    return \
    {
        "source_name": "shodan",
        "status": "completed" if "error" not in normalized else "failed",
        "raw_result": {"infrastructure": normalized},
        "findings": findings,
        "assets": assets
    }