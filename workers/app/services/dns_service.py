import logging
from typing import Any

import dns.resolver

from app.services.whois_service import collect_whois_raw_data

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
            record_text = "".join(
                part.decode("utf-8") for part in record.strings
            )

            raw_result["txt_records"].append(record_text)

            if record_text.startswith("v=spf1"):
                raw_result["spf_records"].append(record_text)

    except Exception as error:
        raw_result["txt_error"] = str(error)

    try:
        dmarc_domain = f"_dmarc.{domain}"
        dmarc_records = dns.resolver.resolve(dmarc_domain, "TXT")

        for record in dmarc_records:
            record_text = "".join(
                part.decode("utf-8") for part in record.strings
            )

            raw_result["dmarc_records"].append(record_text)

    except Exception as error:
        raw_result["dmarc_error"] = str(error)

    return raw_result


def normalize_dns_data(raw_data: JSONDict, whois_data: JSONDict | None = None,) -> JSONDict:
    mx_records = raw_data.get("mx_records", [])
    spf_records = raw_data.get("spf_records", [])
    dmarc_records = raw_data.get("dmarc_records", [])
    detected_services: set[str] = set()

    for record in raw_data.get("txt_records", []):
        if "verification" in record.lower() and "-" in record:
            service_name = record.split("-")[0]
            service_name = service_name.replace("_", " ").title()
            detected_services.add(service_name)

    records: JSONList = []

    records.append({
        "record_type": "MX",
        "status": "Pass" if mx_records else "Warning",
        "finding": (
            "MX records are configured for this domain."
            if mx_records
            else "MX records were not found for this domain."
        ),
    })

    spf_status = "Warning"
    spf_finding = "SPF record was not found in TXT records."

    if spf_records:
        spf_record = spf_records[0].lower()

        if "-all" in spf_record:
            spf_status = "Pass"
            spf_finding = "SPF record is present and uses a hard fail policy."
        elif "~all" in spf_record:
            spf_status = "Warning"
            spf_finding = "SPF record is present but uses a soft fail policy."
        elif "?all" in spf_record:
            spf_status = "Warning"
            spf_finding = "SPF record is present but uses a neutral policy."
        elif "+all" in spf_record:
            spf_status = "Fail"
            spf_finding = "SPF record is present but allows all senders."
        else:
            spf_status = "Warning"
            spf_finding = "SPF record is present, but no explicit all mechanism was detected."

    records.append({
        "record_type": "SPF",
        "status": spf_status,
        "finding": spf_finding,
    })

    dmarc_status = "Warning"
    dmarc_finding = "DMARC record was not found for this domain."

    if dmarc_records:
        dmarc_record = dmarc_records[0].lower()

        if "p=reject" in dmarc_record:
            dmarc_status = "Pass"
            dmarc_finding = "DMARC record is present and uses a reject policy."
        elif "p=quarantine" in dmarc_record:
            dmarc_status = "Pass"
            dmarc_finding = "DMARC record is present and uses a quarantine policy."
        elif "p=none" in dmarc_record:
            dmarc_status = "Warning"
            dmarc_finding = "DMARC record is present but policy is not enforced."

    records.append({
        "record_type": "DMARC",
        "status": dmarc_status,
        "finding": dmarc_finding,
    })

    whois_status = "Unknown"
    whois_finding = "WHOIS/RDAP lookup was not included in this DNS collection."
    normalized_whois: JSONDict = {}
    if whois_data:
        raw_response = whois_data.get("raw_response", {})
        if raw_response:
            whois_status = "Pass"
            whois_finding = "WHOIS/RDAP registration data was available for this domain."
            registrar = "Unknown"

            entities = raw_response.get("entities", [])

            for entity in entities:
                if "registrar" in entity.get("roles", []):
                    vcard = entity.get("vcardArray", [])

                    if len(vcard) > 1:
                        for field in vcard[1]:
                            if field[0] == "fn":
                                registrar = field[3]

            registration_date = None
            expiration_date = None

            for event in raw_response.get("events", []):
                if event.get("eventAction") == "registration":
                    registration_date = event.get("eventDate")

                if event.get("eventAction") == "expiration":
                    expiration_date = event.get("eventDate")

            normalized_whois = {
                "provider": "RDAP",
                "registrar": registrar,
                "registration_date": registration_date,
                "expiration_date": expiration_date,
                "dnssec_enabled": raw_response.get("secureDNS", {}).get("delegationSigned", False),
                "nameservers": [
                    ns.get("ldhName")
                    for ns in raw_response.get("nameservers", [])
                ],
                "status": raw_response.get("status", []),
            }

    records.append({
        "record_type": "WHOIS/RDAP",
        "status": whois_status,
        "finding": whois_finding,
    })

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

    record_map = {
        record.get("record_type"): record
        for record in records
    }

    spf_record = record_map.get("SPF")
    dmarc_record = record_map.get("DMARC")
    mx_record = record_map.get("MX")

    if spf_record and spf_record.get("status") in ["Warning", "Fail"]:
        findings.append({
            "source": "dns",
            "severity": "medium" if spf_record.get("status") == "Fail" else "low",
            "title": "Weak SPF configuration",
            "description": spf_record.get("finding"),
            "recommendation": "Configure SPF to list only authorized mail senders "
            "and avoid permissive policies such as +all.",
            "evidence": spf_record,
        })

    if dmarc_record and dmarc_record.get("status") in ["Warning", "Fail"]:
        findings.append({
            "source": "dns",
            "severity": "medium",
            "title": "Weak or missing DMARC policy",
            "description": dmarc_record.get("finding"),
            "recommendation": "Configure DMARC with quarantine or reject policy "
            "to reduce email spoofing risk.",
            "evidence": dmarc_record,
        })

    if mx_record and mx_record.get("status") == "Warning":
        findings.append({
            "source": "dns",
            "severity": "info",
            "title": "No MX records found",
            "description": mx_record.get("finding"),
            "recommendation": "If the domain should receive email, configure valid MX records. "
            "If not, this may be expected.",
            "evidence": mx_record,
        })

    return findings


def run_dns_scan(domain: str) -> JSONDict:
    raw_dns = collect_dns_raw_data(domain)
    raw_whois = collect_whois_raw_data(domain)
    normalized_dns = normalize_dns_data(raw_dns, raw_whois)
    findings = generate_dns_findings(normalized_dns)

    return {
        "source_name": "dns",
        "status": "completed",
        "raw_result": normalized_dns,
        "findings": findings,
        "assets": [],
    }

