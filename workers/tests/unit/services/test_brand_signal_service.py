from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.brand_signal_service import BrandSignalService


def test_unresolvable_domain(monkeypatch):
    def fail_dns(*args, **kwargs):
        raise Exception("dns failed")

    monkeypatch.setattr("dns.resolver.resolve", fail_dns)

    result = BrandSignalService.gather_signals("missing.example")

    assert result["is_resolvable"] is False
    assert result["ip_addresses"] == []
    assert result["has_mx"] is False
    assert result["has_tls"] is False


def test_resolvable_domain(monkeypatch):
    monkeypatch.setattr(
        "dns.resolver.resolve",
        lambda domain, record_type, lifetime=2.0: ["1.2.3.4"]
        if record_type == "A"
        else [],
    )

    response = MagicMock()
    response.json.return_value = {
        "status": "success",
        "city": "Johannesburg",
        "countryCode": "ZA",
        "isp": "Test ISP",
    }

    monkeypatch.setattr("requests.get", lambda *args, **kwargs: response)

    result = BrandSignalService.gather_signals("example.com")

    assert result["is_resolvable"] is True
    assert result["ip_addresses"] == ["1.2.3.4"]
    assert result["geo_location"] == "Johannesburg, ZA"
    assert result["isp"] == "Test ISP"


def test_mx_records_true(monkeypatch):
    mx_record = SimpleNamespace(exchange="mail.example.com.")

    def fake_dns(domain, record_type, lifetime=2.0):
        if record_type == "A":
            return ["1.2.3.4"]
        if record_type == "MX":
            return [mx_record]

    monkeypatch.setattr("dns.resolver.resolve", fake_dns)

    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: MagicMock(
            json=lambda: {"status": "fail"}
        ),
    )

    result = BrandSignalService.gather_signals("example.com")

    assert result["has_mx"] is True
    assert result["mx_records"] == ["mail.example.com"]


def test_new_domain_registered(monkeypatch):
    monkeypatch.setattr(
        "dns.resolver.resolve",
        lambda domain, record_type, lifetime=2.0: ["1.2.3.4"]
        if record_type == "A"
        else [],
    )

    monkeypatch.setattr(
        "requests.get",
        lambda *args, **kwargs: MagicMock(
            json=lambda: {"status": "fail"}
        ),
    )

    recent_date = datetime.now() - timedelta(days=5)

    monkeypatch.setattr(
        "whois.whois",
        lambda domain: SimpleNamespace(creation_date=recent_date),
    )

    result = BrandSignalService.gather_signals("example.com")

    assert result["days_old"] <= 5
    assert result["is_newly_registered"] is True
    assert result["creation_date"] is not None