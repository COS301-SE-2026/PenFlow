from unittest.mock import patch

from app.tasks.dns_tasks import run_dns_scan


@patch("app.tasks.dns_tasks.send_source_callback")
@patch("app.tasks.dns_tasks.collect_whois_raw_data")
@patch("app.tasks.dns_tasks.collect_dns_raw_data")
def test_dns_scan_happy_path(mock_dns, mock_whois, mock_send_callback):
    mock_dns.return_value = {
        "domain": "acorns.com",
        "mx_records": ["aspmx.l.google.com"],
        "txt_records": [
            "v=spf1 include:_spf.google.com -all",
            "slack-domain-verification=123",
        ],
        "spf_records": [
            "v=spf1 include:_spf.google.com -all",
        ],
        "dmarc_records": [
            "v=DMARC1; p=reject;",
        ],
    }

    mock_whois.return_value = {
        "domain": "acorns.com",
        "provider": "RDAP",
        "raw_response": {
            "entities": [
                {
                    "roles": ["registrar"],
                    "vcardArray": [
                        "vcard",
                        [
                            ["version", {}, "text", "4.0"],
                            ["fn", {}, "text", "Cloudflare, Inc."],
                        ],
                    ],
                }
            ],
            "events": [
                {
                    "eventAction": "registration",
                    "eventDate": "2007-11-26T19:45:36Z",
                },
                {
                    "eventAction": "expiration",
                    "eventDate": "2026-11-26T19:45:36Z",
                },
            ],
            "secureDNS": {
                "delegationSigned": True,
            },
            "nameservers": [
                {"ldhName": "A.NS.ACORNS.COM"},
                {"ldhName": "B.NS.ACORNS.COM"},
            ],
            "status": [
                "client transfer prohibited",
            ],
        },
    }

    result = run_dns_scan("scan-123", "acorns.com")

    assert result["scan_id"] == "scan-123"
    assert result["source_name"] == "dns"
    assert result["status"] == "completed"
    assert result["assets"] == []
    assert result["findings"] == []

    domain_security = result["raw_result"]["domain_security"]

    assert domain_security["provider"] == "DNS/RDAP"
    assert "Slack" in domain_security["detected_services"]

    records = {
        record["record_type"]: record
        for record in domain_security["records"]
    }

    assert records["MX"]["status"] == "Pass"
    assert records["SPF"]["status"] == "Pass"
    assert records["DMARC"]["status"] == "Pass"
    assert records["WHOIS/RDAP"]["status"] == "Pass"

    whois = domain_security["whois"]

    assert whois["provider"] == "RDAP"
    assert whois["registrar"] == "Cloudflare, Inc."
    assert whois["registration_date"] == "2007-11-26T19:45:36Z"
    assert whois["expiration_date"] == "2026-11-26T19:45:36Z"
    assert whois["dnssec_enabled"] is True
    assert whois["nameservers"] == [
        "A.NS.ACORNS.COM",
        "B.NS.ACORNS.COM",
    ]
    mock_send_callback.assert_called_once()


@patch("app.tasks.dns_tasks.send_source_callback")
@patch("app.tasks.dns_tasks.collect_whois_raw_data")
@patch("app.tasks.dns_tasks.collect_dns_raw_data")
def test_dns_scan_missing_email_security_records(mock_dns, mock_whois, mock_send_callback):
    mock_dns.return_value = {
        "domain": "acorns.com",
        "mx_records": [],
        "txt_records": [],
        "spf_records": [],
        "dmarc_records": [],
    }

    mock_whois.return_value = {
        "domain": "acorns.com",
        "provider": "RDAP",
        "raw_response": {},
        "error": "RDAP unavailable",
    }

    result = run_dns_scan("scan-123", "acorns.com")

    assert result["status"] == "completed"

    domain_security = result["raw_result"]["domain_security"]

    records = {
        record["record_type"]: record
        for record in domain_security["records"]
    }

    assert records["MX"]["status"] == "Warning"
    assert records["SPF"]["status"] == "Warning"
    assert records["DMARC"]["status"] == "Warning"
    assert records["WHOIS/RDAP"]["status"] == "Unknown"

    finding_titles = [
        finding["title"]
        for finding in result["findings"]
    ]

    assert "Weak SPF configuration" in finding_titles
    assert "Weak or missing DMARC policy" in finding_titles
    assert "No MX records found" in finding_titles
    mock_send_callback.assert_called_once()


@patch("app.tasks.dns_tasks.send_source_callback")
@patch("app.tasks.dns_tasks.collect_whois_raw_data")
@patch("app.tasks.dns_tasks.collect_dns_raw_data")
def test_dns_scan_detects_spf_fail_policy(mock_dns, mock_whois, mock_send_callback):
    mock_dns.return_value = {
        "domain": "acorns.com",
        "mx_records": ["mail.acorns.com"],
        "txt_records": [
            "v=spf1 +all",
        ],
        "spf_records": [
            "v=spf1 +all",
        ],
        "dmarc_records": [
            "v=DMARC1; p=none;",
        ],
    }

    mock_whois.return_value = {
        "domain": "acorns.com",
        "provider": "RDAP",
        "raw_response": {},
    }

    result = run_dns_scan("scan-123", "acorns.com")

    domain_security = result["raw_result"]["domain_security"]

    records = {
        record["record_type"]: record
        for record in domain_security["records"]
    }

    assert records["SPF"]["status"] == "Fail"
    assert records["DMARC"]["status"] == "Warning"

    severities = {
        finding["title"]: finding["severity"]
        for finding in result["findings"]
    }

    assert severities["Weak SPF configuration"] == "medium"
    assert severities["Weak or missing DMARC policy"] == "medium"
    mock_send_callback.assert_called_once()