import ssl
from datetime import datetime
from typing import Any

import dns.resolver
import whois

from app.utils.safe_outbound import (
    normalise_host,
    public_connection,
    resolve_public_host,
    safe_get,
)


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
            "creation_date": None,
            "days_old": None,
            "is_newly_registered": False,
            "geo_location": None,
            "isp": None,
        }

        try:
            domain = normalise_host(domain)

            signals["ip_addresses"] = resolve_public_host(
                domain,
                timeout=2.0,
            )
            signals["is_resolvable"] = bool(
                signals["ip_addresses"]
            )

        except Exception as error:
            signals["collection_error"] = str(error)
            return signals

        if not signals["is_resolvable"]:
            return signals

        try:
            primary_ip = signals["ip_addresses"][0]
            resp = safe_get(
                f"http://ip-api.com/json/{primary_ip}",
                timeout=2.0,
                max_bytes=64 * 1024,
            ).json()
            if resp.get("status") == "success":
                signals["geo_location"] = (
                    f"{resp.get('city', 'Unknown')}, {resp.get('countryCode', '')}"
                )
                signals["isp"] = resp.get("isp")
        except Exception:
            pass

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
            with public_connection(
                domain,
                443,
                timeout=2.0,
            ) as sock:
                with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert() or {}
                    signals["has_tls"] = True
                    signals["tls_issuer"] = str(cert.get("issuer", ""))
        except Exception:
            pass

        try:
            w = whois.whois(domain)
            if w.creation_date:
                creation = (
                    w.creation_date[0] if isinstance(w.creation_date, list) else w.creation_date
                )
                creation = creation.replace(tzinfo=None)
                signals["creation_date"] = creation.isoformat()
                signals["days_old"] = (datetime.now() - creation).days
                signals["is_newly_registered"] = signals["days_old"] < 30
        except Exception:
            pass

        return signals
