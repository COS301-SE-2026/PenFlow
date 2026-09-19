import sys 
import argparse 
import json 
import logging 
from typing import Any 

from app.services.nmap_service import run_live_nmap_scan 
from app.services.tls_service import run_tls_scan 
from app.services.http_security_service import run_http_security_scan 
from app.services.fingerprinting_service import FingerprintingService 
from app.utils.callback import send_source_callback 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def safe_failure_callback(scan_id: str, source_name: str, error: Exception) -> None: 
    try: 
        send_source_callback(
            scan_id=scan_id,
            source_name=source_name, 
            status="failed", 
            raw_result={"error": str(error)}, 
            error_message=str(error)
        )
    except Exception as cb_e: 
        logger.error(f"Failed to send failures callback for {source_name}: {cb_e}")

def handle_nmap(payload: dict[str, Any]) -> None: 
    scan_id = payload["scan_id"]
    try:
        send_source_callback(scan_id=scan_id, source_name="nmap", status="running")
        scan_data = run_live_nmap_scan(ip_address=payload["ip_address"], profile=payload.get("profile", "standard"))

        services = [
            {
                "host": scan_data["ip"], "port": p["port"], "protocol": p["protocol"],
                "service_name": p["service"], "product": p["product"], "version": p["version"], 
                "banner": p.get("extra_info"), "state": p["state"], "tls_enabled": False,
            } for p in scan_data.get("ports", [])
        ]
        send_source_callback(scan_id=scan_id, source_name="nmap", status="completed", raw_result=scan_data, services=services)
    except Exception as error:
        logger.exception(f"NMAP failed: {error}")
        safe_failure_callback(scan_id, "nmap", error)
        raise 

def handle_tls(payload: dict[str, Any]) -> None:
    scan_id = payload["scan_id"]
    ip_address = payload["ip_address"]
    try:
        send_source_callback(scan_id=scan_id, source_name="tls", status="running")
        tls_data = run_tls_scan(ip_address=ip_address, ports=payload["ports"], hostname=payload.get("hostname"))

        findings = []
        for target in tls_data.get("targets", []):
            if "error" in target:
                findings.append({
                    "source": "tls",  "title": "TLS Handshake Failed", "description": target["error"], 
                    "recommendation": "Review TLS configuration.", "severity": "low", 
                    "host": ip_address, "port": target["port"], "protocol": "tcp", "evidence": {"error": target["error"]}
                })
                continue 

            cert = target.get("certificate", {})
            if cert.get("expired"): 
                findings.append({
                    "source": "tls", "title": "Expired TLS Certificate", "description": "The TLS certificate has expired.", 
                    "recommendation": "Renew the certificate.", "severity": "high",
                    "host": ip_address, "port": target["port"], "protocol": "tcp", "evidence": cert
                })
            if cert.get("self_signed"): 
                findings.append({
                    "source": "tls", "title": "Self-Signed TLS Certificate", "description": "Using a self-signed certificate.", 
                    "recommendation": "Use a trusted CA.", "severity": "medium", 
                    "host": ip_address, "port": target["port"], "protocol": "tcp", "evidence": {"subject": cert.get("subject"), "issuer": cert.get("issuer")} 
                })

        send_source_callback(scan_id=scan_id, source_name="tls", status="completed", raw_result=tls_data, findings=findings)
    except Exception as error: 
        logger.exception(f"TLS failed: {error}")
        safe_failure_callback(scan_id, "tls", error)
        raise 

def handle_http_security(payload: dict[str, Any]) -> None: 
    scan_id = payload["scan_id"] 
    ip_address = payload["ip_address"] 
    try: 
        send_source_callback(scan_id=scan_id, source_name="http_security", status="running")
        scan_data = run_http_security_scan(hostname=payload.get("hostname"), ip_address=ip_address, ports=payload["ports"])

        findings = [] 
        for target in scan_data.get("targets", []):
            headers = target.get("security_headers", {})
            if not headers.get("content_security_policy") and not headers.get("content_security_policy_report_only"): 
                findings.append({
                    "source": "http_security", "severity": "low", "title": "Missing Content-Security-Policy", 
                     "description": "No CSP present.", "recommendation": "Create a CSP header.", 
                     "host": ip_address, "port": target["port"], "protocol": "tcp", "evidence": {"url": target["url"], "header": "Content-Security-Policy"}
                })

            checks = {
                "X-Frame-Options": headers.get("x_frame_options"), 
                "Referrer-Policy": headers.get("referrer_policy"), 
                "Permissions-Policy": headers.get("permissions_policy"), 
                "X-Content-Type-Options": headers.get("x_content_type_options"),
            }
            if target.get("scheme") == "https": 
                checks["Strict-Transport-Security"] = headers.get("strict_transport_security")

            for h_name, h_val in checks.items(): 
                if not h_val: 
                    findings.append({
                        "source": "https_security", "severity": "low", "title": f"Missing {h_name}", 
                        "description": f"{h_name} missing.", "recommendation": f"Configure {h_name}.",
                        "host": ip_address, "port": target["port"], "protocol": "tcp", "evidence": {"url": target["url"], "header": h_name}
                    })

        send_source_callback(scan_id=scan_id, source_name="http_security", status="completed", raw_result=scan_data, findings=findings)
    except Exception as error:
        logger.exception(f"HTTP Security failed: {error}")
        safe_failure_callback(scan_id, "http_security", error)
        raise 