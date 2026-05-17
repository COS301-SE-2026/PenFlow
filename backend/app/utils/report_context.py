from datetime import datetime, timezone

SEVERITIES = ["critical", "high", "medium", "low", "info"]


def get_value(obj, key, default=None):
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(key, default)

    return getattr(obj, key, default)


def get_source(scan_sources, source_name):
    for source in scan_sources or []:
        name = get_value(source, "source_name", "")

        if name.lower() == source_name.lower():
            return source

    return None


def get_raw_result(scan_sources, source_name):
    source = get_source(scan_sources, source_name)
    return get_value(source, "raw_result", {}) or {}


def calculate_severity_counts(findings):
    counts = {severity: 0 for severity in SEVERITIES}

    for finding in findings or []:
        severity = get_value(finding, "severity", "info").lower()

        if severity in counts:
            counts[severity] += 1
        else:
            counts["info"] += 1

    return counts


def format_generated_at(value=None):
    if value is None:
        value = datetime.now(timezone.utc)

    if isinstance(value, str):
        return value

    return value.strftime("%d %B %Y")


def build_infrastructure_context(scan_sources):
    raw = get_raw_result(scan_sources, "shodan")
    infrastructure = raw.get("infrastructure", raw)

    ip_addresses = infrastructure.get("ip_addresses", [])
    open_ports = infrastructure.get("open_ports", [])
    ip_address = "Unknown"

    if ip_addresses:
        ip_address = ip_addresses[0].get("ip_str", "Unknown")

    return {
        "hosting_provider": infrastructure.get("hosting_provider", "Unknown"),
        "ip_address": ip_address,
        "open_ports": open_ports,
    }


def build_tech_stack_context(scan_sources):
    raw = get_raw_result(scan_sources, "wappalyzer")
    tech_stack = raw.get("tech_stack", raw)

    technologies_used = []

    for category_items in tech_stack.values():
        if isinstance(category_items, list):
            for item in category_items:
                technologies_used.append({
                    "name": item.get("name", "Unknown"),
                    "version": item.get("version", "Unknown")
                })

    return technologies_used


def build_subdomains_context(scan_sources):
    raw = get_raw_result(scan_sources, "crt.sh")
    subdomains = raw.get("subdomains", raw)

    discovered_names = subdomains.get("discovered_names", [])
    
    return {
        "total_found": len(discovered_names),
        "discovered_names": discovered_names,
    }


def build_reputation_context(scan_sources):
    raw = get_raw_result(scan_sources, "urlscan")
    reputation = raw.get("reputation", raw)

    return {
        "malicious_flags": reputation.get("malicious_flags", 0),
        "urlscan_uuid": reputation.get("urlscan_uuid", "Unavailable"),
        "screenshot_url": reputation.get("screenshot_url", "default_screenshot.png")
    }


def build_phishing_surface_context(scan_sources):
    raw = get_raw_result(scan_sources, "hunter.io")
    phishing_surface = raw.get("phishing_surface", raw)

    return {
        "public_emails_found": phishing_surface.get("public_emails_found", []),
    }


def build_breach_data_context(scan_sources):
    raw = get_raw_result(scan_sources, "hibp")
    breach_data = raw.get("breach_data", raw)

    pwned_accounts_count = breach_data.get("pwned_accounts_count", 0)

    severity = "info"
    if pwned_accounts_count > 0:
        severity = "medium"

    return {
        "severity": severity,
        "pwned_accounts_count": pwned_accounts_count,
        "known_breaches": breach_data.get("known_breaches", []),
    }


def build_domain_security_context(scan_sources):
    raw = get_raw_result(scan_sources, "dns")
    domain_security = raw.get("domain_security", raw)

    if domain_security:
        return domain_security

    # Full mock for now, since there is currently no normalized reponse for it
    return [
        {
            "record_type": "MX",
            "status": "Unknown",
            "finding": "MX record data was not available for this scan.",
        },
        {
            "record_type": "SPF",
            "status": "Unknown",
            "finding": "SPF record data was not available for this scan.",
        },
        {
            "record_type": "DMARC",
            "status": "Unknown",
            "finding": "DMARC record data was not available for this scan.",
        },
        {
            "record_type": "WHOIS",
            "status": "Unknown",
            "finding": "WHOIS data was not available for this scan.",
        },
    ]
