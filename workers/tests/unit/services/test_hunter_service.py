from app.services.hunter_service import (
    generate_findings_and_assets,
    normalize_data,
)


def test_normalize():
    raw = \
    {
        "data":
        {
            "pattern": "{first}.{last}",
            "emails":
            [
                {
                    "value": "jerry@tester.com",
                    "type": "personal",
                    "confidence": 90,
                }
            ],
        }
    }

    result = normalize_data(raw)
    emails = result["phishing_surface"]["public_emails_found"]
    assert len(emails) == 1
    assert emails[0]["email"] == "jerry@tester.com"


def test_normalize_error():
    result = normalize_data({"error": "failed"})
    assert result["error"] == "failed"


def test_findings():
    data = \
    {
        "phishing_surface":
        {
            "email_format_pattern": "{first}.{last}",
            "public_emails_found":
            [
                {
                    "email": "bob@tester.com",
                }
            ],
        }
    }

    findings, assets = generate_findings_and_assets(data)
    assert len(findings) == 1
    assert len(assets) == 1


def test_no_findings():
    findings, assets = (generate_findings_and_assets
    (
        {"error": "failed"}
    ))

    assert findings == []
    assert assets == []