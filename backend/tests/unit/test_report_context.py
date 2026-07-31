from app.utils.report_context import build_report_context


#phase 2 GET /scans/{scan_id}/pdf download_scan_pdf  normalized data
def test_build_report_context_from_normalized_data():
    scan = {
        "id": "10337236-d819-43fd-b878-9c911f0d09ae",
        "domain": "hackerone.com",
        "status": "completed",
    }

    findings = [
        {"severity": "high", "recommendation": "Review exposed services."},
        {"severity": "medium", "recommendation": "Review exposed emails."},
        {"severity": "info", "recommendation": "Review discovered subdomains."},
    ]

    scan_sources = [
        {
            "source_name": "shodan",
            "raw_result": {
                "infrastructure": {
                    "hosting_provider": "Cloudflare, Inc.",
                    "ip_addresses": [{"ip_str": "104.16.99.52"}],
                    "open_ports": [{"port": 80, "state": "open"}],
                }
            },
        }
    ]

    context = build_report_context(scan, findings, scan_sources)

    assert context["target_domain"] == "hackerone.com"
    assert context["severity_counts"]["high"] == 1
    assert context["severity_counts"]["medium"] == 1
    assert context["severity_counts"]["info"] == 1
    assert context["infrastructure"]["hosting_provider"] == "Cloudflare, Inc."
    assert context["infrastructure"]["open_ports"][0]["port"] == 80