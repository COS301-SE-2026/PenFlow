from decimal import Decimal
from types import SimpleNamespace
from app.utils.phase2_report_context import (
    build_phase2_report_context,
    calc_avg_cvss,
    calc_severity_counts,
)


def test_report_happy():
    scan = (SimpleNamespace
    (
        id="12345678-aaaa-bbbb-cccc-123456789012",
        domain="jerry.com",
        status="completed",
    ))

    findings =\
    [
        {
            "id":"finding-1",
            "title":"Jerry forgot the patch",
            "severity":"high",
            "status":"open",
            "source":"bob",
            "cve_id":"CVE-123",
            "cvss_score":Decimal("8.5"),
            "asset_id":"asset-1",
            "service_id":"service-1",
        }
    ]

    assets =\
    [
        {
            "id":"asset-1",
            "identifier":"jerry.com",
            "asset_type":"domain",
        }
    ]

    services =\
    [
        {
            "id":"service-1",
            "host":"jerry.com",
            "port":443,
            "protocol":"tcp",
            "service_name":"https",
        }
    ]

    result = (build_phase2_report_context
    (
        scan,
        findings,
        assets,
        services,
        [],
        [],
    ))

    assert result["target_domain"] == "jerry.com"
    assert result["summary"]["high_count"] == 1
    assert result["vulnerabilities"]["cve_count"] == 1


def test_report_empty():
    result = (build_phase2_report_context
    (
        {"id":"bob12345","domain":"bob.com"},
        [],
        [],
        [],
        [],
        [],
    ))

    assert result["summary"]["total_findings"] == 0
    assert result["vulnerabilities"]["highest_cvss"] is None


def test_severity_sad():
    result = (calc_severity_counts
    (
        [
            {"severity":"critical"},
            {"severity":"banana"},
        ]
    ))

    assert result["critical"] == 1
    assert result["info"] == 1


def test_cvss():
    result = (calc_avg_cvss
    (
        [
            {"cvss_score":Decimal("8.0")},
            {"cvss_score":6.0},
        ]
    ))

    assert result == 7.0