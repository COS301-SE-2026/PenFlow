import logging
import dns.resolver

logger = logging.getLogger(__name__)


def collect_dns_raw_data(domain: str) -> dict:
    """
    Collects raw DNS records for a domain, used before normalization.
    """
    logger.info("Collecting DNS data for domain: %s", domain)

    raw_result = {
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
