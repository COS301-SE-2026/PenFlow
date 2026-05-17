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


