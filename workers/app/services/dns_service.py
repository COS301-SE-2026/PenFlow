import logging
from typing import Any

import dns.resolver

JSONDict = dict[str, Any]
JSONList = list[JSONDict]

logger = logging.getLogger(__name__)


def collect_dns_raw_data(domain: str) -> JSONDict:
    """
    Collects raw DNS records for a domain, used before normalization.
    """
    logger.info("Collecting DNS data for domain: %s", domain)

    raw_result: JSONDict = {
        "domain": domain,
        "mx_records": [],
        "txt_records": [],
        "spf_records": [],
        "dmarc_records": [],
    }

    try:
        mx_records = dns.resolver.resolve(domain, "MX")

        for record in mx_records:
            raw_result["mx_records"].append(str(record.exchange).rstrip("."))

    except Exception as error:
        raw_result["mx_error"] = str(error)

    try:
        txt_records = dns.resolver.resolve(domain, "TXT")

        for record in txt_records:
            record_text = "".join(part.decode("utf-8") for part in record.strings)

            raw_result["txt_records"].append(record_text)

            if record_text.startswith("v=spf1"):
                raw_result["spf_records"].append(record_text)

    except Exception as error:
        raw_result["txt_error"] = str(error)

    try:
        dmarc_domain = f"_dmarc.{domain}"
        dmarc_records = dns.resolver.resolve(dmarc_domain, "TXT")

        for record in dmarc_records:
            record_text = "".join(part.decode("utf-8") for part in record.strings)

            raw_result["dmarc_records"].append(record_text)

    except Exception as error:
        raw_result["dmarc_error"] = str(error)

    return raw_result


_SERVICE_MAPPING: dict[str, str] = {
    "adobe": "Adobe",
    "anthropic": "Anthropic",
    "apple": "Apple",
    "atlassian": "Atlassian",
    "box": "Box",
    "canva": "Canva",
    "citrix": "Citrix",
    "docusign": "DocuSign",
    "drift": "Drift",
    "facebook": "Facebook",
    "google-site-verification": "Google",
    "jetbrains": "JetBrains",
    "monday": "Monday.com",
    "openai": "OpenAI",
    "slack": "Slack",
    "stripe": "Stripe",
    "zoom": "Zoom",
}


def _guess_service_from_verification_record(record: str, record_lower: str) -> str | None:
    if "verification" not in record_lower or "-" not in record:
        return None

    candidate = record.split("-")[0].replace("_", " ").title()

    if len(candidate) <= 2:
        return None

    return candidate


def _detect_services(txt_records: list[str]) -> set[str]:
    detected: set[str] = set()

    for record in txt_records:
        record_lower = record.lower()

        matched_services = [svc for kw, svc in _SERVICE_MAPPING.items() if kw in record_lower]

        if matched_services:
            detected.update(matched_services)
            continue

        guessed_service = _guess_service_from_verification_record(record, record_lower)

        if guessed_service:
            detected.add(guessed_service)

    return detected


def _analyze_spf(spf_records: list[str]) -> tuple[str, str]:
    if not spf_records:
        return "Warning", "SPF record was not found in TXT records."
    rec = spf_records[0].lower()
    if "-all" in rec:
        return "Pass", "SPF record is present and uses a hard fail policy."
    if "~all" in rec:
        return "Warning", "SPF record is present but uses a soft fail policy."
    if "?all" in rec:
        return "Warning", "SPF record is present but uses a neutral policy."
    if "+all" in rec:
        return "Fail", "SPF record is present but allows all senders."
    return "Warning", "SPF record is present, but no explicit all mechanism was detected."


def _analyze_dmarc(dmarc_records: list[str]) -> tuple[str, str]:
    if not dmarc_records:
        return "Warning", "DMARC record was not found for this domain."
    rec = dmarc_records[0].lower()
    if "p=reject" in rec:
        return "Pass", "DMARC record is present and uses a reject policy."
    if "p=quarantine" in rec:
        return "Pass", "DMARC record is present and uses a quarantine policy."
    if "p=none" in rec:
        return "Warning", "DMARC record is present but policy is not enforced."
    return "Warning", "DMARC record was not found for this domain."


def _extract_registrar(entities: list[JSONDict]) -> str:
    for entity in entities:
        if "registrar" in entity.get("roles", []):
            vcard = entity.get("vcardArray", [])
            if len(vcard) > 1:
                for field in vcard[1]:
                    if field[0] == "fn":
                        return str(field[3])
    return "Unknown"


def _extract_event_dates(events: list[JSONDict]) -> tuple[str | None, str | None]:
    registration_date = None
    expiration_date = None
    for event in events:
        if event.get("eventAction") == "registration":
            registration_date = event.get("eventDate")
        if event.get("eventAction") == "expiration":
            expiration_date = event.get("eventDate")
    return registration_date, expiration_date


def _normalize_whois(whois_data: JSONDict | None) -> tuple[str, str, JSONDict]:
    _missing = "Unknown", "WHOIS/RDAP lookup was not included in this DNS collection.", {}
    if not whois_data:
        return _missing
    raw_response = whois_data.get("raw_response", {})
    if not raw_response:
        return _missing

    registration_date, expiration_date = _extract_event_dates(raw_response.get("events", []))
    normalized: JSONDict = {
        "provider": "RDAP",
        "registrar": _extract_registrar(raw_response.get("entities", [])),
        "registration_date": registration_date,
        "expiration_date": expiration_date,
        "dnssec_enabled": raw_response.get("secureDNS", {}).get("delegationSigned", False),
        "nameservers": [ns.get("ldhName") for ns in raw_response.get("nameservers", [])],
        "status": raw_response.get("status", []),
    }
    return "Pass", "WHOIS/RDAP registration data was available for this domain.", normalized


def normalize_dns_data(raw_data: JSONDict, whois_data: JSONDict | None = None) -> JSONDict:
    mx_records = raw_data.get("mx_records", [])
    detected_services = _detect_services(raw_data.get("txt_records", []))
    spf_status, spf_finding = _analyze_spf(raw_data.get("spf_records", []))
    dmarc_status, dmarc_finding = _analyze_dmarc(raw_data.get("dmarc_records", []))
    whois_status, whois_finding, normalized_whois = _normalize_whois(whois_data)

    records: JSONList = [
        {
            "record_type": "MX",
            "status": "Pass" if mx_records else "Warning",
            "finding": (
                "MX records are configured for this domain."
                if mx_records
                else "MX records were not found for this domain."
            ),
        },
        {"record_type": "SPF", "status": spf_status, "finding": spf_finding},
        {"record_type": "DMARC", "status": dmarc_status, "finding": dmarc_finding},
        {"record_type": "WHOIS/RDAP", "status": whois_status, "finding": whois_finding},
    ]

    return {
        "domain_security": {
            "provider": "DNS/RDAP",
            "records": records,
            "whois": normalized_whois,
            "detected_services": sorted(list(detected_services)),
        }
    }


def generate_dns_findings(normalized_dns: JSONDict) -> JSONList:
    domain_security = normalized_dns.get("domain_security", {})
    records = domain_security.get("records", [])
    findings: JSONList = []

    record_map = {record.get("record_type"): record for record in records}

    spf_record = record_map.get("SPF")
    dmarc_record = record_map.get("DMARC")
    mx_record = record_map.get("MX")

    if spf_record and spf_record.get("status") in ["Warning", "Fail"]:
        findings.append(
            {
                "source": "dns",
                "severity": "medium" if spf_record.get("status") == "Fail" else "low",
                "title": "Weak SPF configuration",
                "description": spf_record.get("finding"),
                "recommendation": "Configure SPF to list only authorized mail senders "
                "and avoid permissive policies such as +all.",
                "evidence": spf_record,
            }
        )

    if dmarc_record and dmarc_record.get("status") in ["Warning", "Fail"]:
        findings.append(
            {
                "source": "dns",
                "severity": "medium",
                "title": "Weak or missing DMARC policy",
                "description": dmarc_record.get("finding"),
                "recommendation": "Configure DMARC with quarantine or reject policy "
                "to reduce email spoofing risk.",
                "evidence": dmarc_record,
            }
        )

    if mx_record and mx_record.get("status") == "Warning":
        findings.append(
            {
                "source": "dns",
                "severity": "info",
                "title": "No MX records found",
                "description": mx_record.get("finding"),
                "recommendation": "If the domain should receive email, configure valid MX records. "
                "If not, this may be expected.",
                "evidence": mx_record,
            }
        )

    return findings
