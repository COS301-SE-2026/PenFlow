from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

JSONDict = dict[str, Any]
JSONObject = dict[str, Any] | object

SEVERITY = {
    "critical",
    "high",
    "medium",
    "low",
    "info",
}

def get_val(obj: JSONObject | None, key: str, default: Any | None = None) -> Any:
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(key, default)

    return getattr(obj, key, default)


def get_enum_val(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value

    return value


def format_timestamp(value: datetime | None = None) -> str:
    if value is None:
        value = datetime.now(timezone.utc)

    return value.strftime("%d %B %Y")


def calc_severity_counts(findings: list[JSONObject] | None) -> dict[str, int]:
    counts = dict.fromkeys(SEVERITY, 0)

    for finding in findings or []:
        severity = get_enum_val(
            get_val(finding, "severity", "info")
        )

        severity = str(severity).lower()

        if severity in counts:
            counts[severity] += 1
        else:
            counts["info"] += 1

    return counts


def calc_avg_cvss(findings: list[JSONObject] | None) -> float | None:
    scores: list[float] = []

    for finding in findings or []:
        score = get_val(finding, "cvss_score")

        if score is None:
            continue

        if isinstance(score, Decimal):
            score = float(score)

        scores.append(float(score))

    if not scores:
        return None

    return round(sum(scores) / len(scores), 1)


def build_summary_context(
        findings: list[JSONObject] | None,
        assets: list[JSONObject] | None,
        services: list[JSONObject] | None,
        technologies: list[JSONObject] | None,
) -> JSONDict:
    severity_counts = calc_severity_counts(findings)

    return {
        "total_findings": len(findings or []),
        "critical_count": severity_counts["critical"],
        "high_count": severity_counts["high"],
        "medium_count": severity_counts["medium"],
        "low_count": severity_counts["low"],
        "info_count": severity_counts["info"],
        "asset_count": len(assets or []),
        "service_count": len(services or []),
        "technology_count": len(technologies or []),
        "average_cvss": calc_avg_cvss(findings),
    }


def build_findings_context(
        findings: list[JSONObject] | None,
        assets: list[JSONObject] | None,
        services: list[JSONObject] | None,
) -> list[JSONDict]:
    asset_map = {
        get_val(asset, "id"): asset 
        for asset in assets or []
    }

    service_map = {
        get_val(service, "id"): service 
        for service in services or []
    }

    result: list[JSONDict] = []

    for finding in findings or []:
        asset_id = get_val(finding, "asset_id")

        service_id = get_val(finding, "service_id")

        asset = asset_map.get(asset_id)
        service = service_map.get(service_id)

        cvss_score = get_val(finding, "cvss_score")

        if isinstance(cvss_score, Decimal):
            cvss_score = float(cvss_score)

        result.append(
            {
                "id": str(get_val(finding, "id", "")),
                "title": get_val(finding, "title", "Unknown Finding"),
                "severity": str(get_enum_val(get_val(finding, "severity", "info"))).lower(),
                "status": str(get_enum_val(get_val(finding, "status", "open"))).lower(),
                "source": get_val(finding, "source", "Unknwon"),
                "cve_id": get_val(finding, "cve_id"),
                "cvss_score": cvss_score,
                "description": get_val(finding, "description"),
                "recommendation": get_val(finding, "recommendation"),
                "evidence": get_val(finding, "evidence", {}) or {},
                "asset": (get_val(asset, "identifier") if asset else None),
                "service": (
                    {
                        "host": get_val(service, "host"),
                        "port": get_val(service, "port"),
                        "protocol": get_val(service, "protocol"),
                        "service_name": get_val(service, "service_name")
                    } if service else None
                ),
            }
        )
    return result


def build_assets_context(
        assets: list[JSONObject] | None,
        findings: list[JSONObject] | None,
) -> list[JSONDict]:
    result: list[JSONDict] = []

    for asset in assets or []:
        asset_id = get_val(asset, "id")

        asset_findings = [
            finding for finding in findings or []
            if get_val(finding, "asset_id") == asset_id
        ]

        severity_counts = calc_severity_counts(asset_findings)

        result.append(
            {
                "identifier": get_val(asset, "identifier", "Unknown"),
                "asset_type": get_val(asset, "asset_type", "Unknown"),
                "findings_count": len(asset_findings),
                "critical_count": severity_counts["critical"],
                "high_count": severity_counts["high"],
                "medium_count": severity_counts["medium"],
                "low_count": severity_counts["low"],
                "info_count": severity_counts["info"],
            }
        )

    return result


def build_services_context(
        services: list[JSONObject] | None,
        findings: list[JSONObject] | None,
) -> list[JSONDict]:
    result: list[JSONDict] = []

    for service in services or []:
        service_id = get_val(service, "id")

        service_findings = [
            finding for finding in findings or []
            if get_val(finding, "service_id") == service_id
        ]

        result.append(
            {
                "host": get_val(service, "host", "Unknown"),
                "port": get_val(service, "port"),
                "protocol": get_val(service, "protocol", "Unknown"),
                "service_name": get_val(service, "service_name"),
                "product": get_val(service, "product"),
                "version": get_val(service, "version"),
                "state": get_val(service, "state", "open"),
                "tls_enabled": get_val(service, "tls_enabled", False),
                "findings_count": len(service_findings)
            }
        )

    return result


def build_tech_context(
        technologies: list[JSONObject] | None,
        assets: list[JSONObject] | None,
        services: list[JSONObject] | None,
) -> list[JSONDict]:
    asset_map = {
        get_val(asset, "id"): asset
        for asset in assets or []
    }

    services_map = {
        get_val(services, "id"): service
        for service in services or []
    }

    result = []

    for technology in technologies or []:
        confidence = get_val(technology, "confidence")

        if isinstance(confidence, Decimal):
            confidence = float(confidence)

        asset = asset_map.get(
            get_val(technology, "asset_id")
        )

        service = services_map.get(
            get_val(technology, "service_id")
        )

        result.append(
            {
                "technology_type": get_val(technology, "technology_type", "Unknown"),
                "product": get_val(technology, "product", "Unknown"),
                "version": get_val(technology, "version"),
                "confidence": confidence,
                "detection_source": get_val(technology, "detection_source"),
                "evidence": (get_val(technology, "evidence", {}) or {}),
                "asset": (get_val(asset, "identifier") if asset else None),
                "service": (
                    {
                        "host": get_val(service, "host"),
                        "port": get_val(service, "port"),
                        "protocol": get_val(service, "protocol"),
                    } if service else None
                ),
            }
        )

    return result


def build_scan_sources_context(
        scan_sources: list[JSONObject] | None
) -> list[JSONDict]:
    result = []

    for source in scan_sources or []:
        result.append(
            {
                "source_name": get_val(source, "source_name", "Unknown"),
                "status": str(get_enum_val(get_val(source, "status", "Unknown"))),
                "error_message": get_val(source, "error_message"),
            }
        )

    return result


def build_vulnerability_summary(
        findings: list[JSONObject] | None
) -> JSONDict:
    cve_findings = [
        finding for finding in findings or []
        if get_val(finding, "cve_id")
    ]

    scores = [
        float(get_val(finding, "cvss_score"))
        for finding in cve_findings
        if get_val(finding, "cvss_score") is not None
    ]

    return {
        "cve_count": len(cve_findings),
        "highest_cvss": (max(scores) if scores else None),
        "average_cvss": (
            round(sum(scores) / len(scores), 1)
            if scores else None
        ),
    }


def build_phase2_report_context(
        scan: JSONObject,
        findings: list[JSONObject] | None,
        assets: list[JSONObject] | None,
        services: list[JSONObject] | None,
        technologies: list[JSONObject] | None,
        scan_sources: list[JSONObject] | None,
) -> JSONDict:
    scan_id = str(get_val(scan, "id", "unknown scan id"))

    scan_status = get_enum_val(get_val(scan, "status", 'completed'))

    return {
        "target_domain": get_val(scan, "domain", "Unknown domain"),
        "report_id": f"PF-{scan_id[:8]}",
        "generated_at": format_timestamp(),
        "status": str(scan_status).replace("_", " ").title(),
        "severity_counts": calc_severity_counts(findings),
        "summary": build_summary_context(
            findings=findings,
            assets=assets,
            services=services,
            technologies=technologies,
        ),
        "findings": build_findings_context(
            findings=findings,
            assets=assets,
            services=services,
        ),
        "assets": build_assets_context(
            assets=assets,
            findings=findings,
        ),
        "services": build_services_context(
            services=services,
            findings=findings,
        ),
        "technologies": build_tech_context(
            technologies=technologies,
            assets=assets,
            services=services,
        ),
        "scan_sources": build_scan_sources_context(scan_sources=scan_sources),
        "vulnerabilities": build_vulnerability_summary(findings=findings),
    }