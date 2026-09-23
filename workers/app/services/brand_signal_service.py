import socket 
import ssl 
import dns.resolver 
from typing import Any 

class BrandSignalService:
    @staticmethod 
    def gather_signals(domain: str) -> dict[str, Any]:
        signals: dict[str, Any] = {
            "is_resolvable": False,
            "ip_addresses": [],
            "has_mx": False,
            "mx_records": [],
            "has_tls": False,
            "tls_issuer": None,
        }

        try:
            answers = dns.resolver.resolve(domain, "A", lifetime=2.0)
            signals["ip_addresses"] = [str(rdata) for rdata in answers]
            signals["is_resolvable"] = len(signals["ip_addresses"]) > 0
        except Exception:
            pass 

        if not signals["is_resolvable"]:
            return signals 

        try:
            mx_answers = dns.resolver.resolve(domain, "MX", lifetime=2.0)
            signals["mx_records"] = [str(rdata.exchange).rstrip(".") for rdata in mx_answers]
            signals["has_mx"] = len(signals["mx_records"]) > 0
        except Exception:
            pass 

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False 
            ctx.verify_mode = ssl.CERT_NONE 
            with socket.create_connection((domain, 443), timeout=2.0) as sock:
                with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    signals["has_tls"] = True 
                    signals["tls_issuer"] = str(cert.get("issuer", ""))
        except Exception:
            pass
        return signals