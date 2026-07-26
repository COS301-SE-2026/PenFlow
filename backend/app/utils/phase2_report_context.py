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

def get_val(obj: JSONObject | None, key: str, default: Any | None) -> Any:
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
            get_val(
                finding,
                "severity",
                "info",
            )
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
        score = get_val(
            finding,
            "cvss_score",
        )

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