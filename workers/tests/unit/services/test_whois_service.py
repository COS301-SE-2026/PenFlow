import httpx
from unittest.mock import MagicMock
from app.services.whois_service import collect_whois_raw_data


def test_whois(monkeypatch):
    response = MagicMock()
    response.status_code = 200
    response.url = "https://rdap.org/domain/jerry.com"
    response.json.return_value = \
    {
        "ldhName": "jerry.com",
        "handle": "JERRY123",
    }
    client = MagicMock()
    client.__enter__.return_value = client
    client.get.return_value = response
    (monkeypatch.setattr
    (
        "app.services.whois_service.httpx.Client",
        lambda **kwargs: client,
    ))
    result = collect_whois_raw_data("jerry.com")
    assert result["domain"] == "jerry.com"
    assert result["provider"] == "RDAP"
    assert result["status_code"] == 200


def test_whois_http_failed(monkeypatch):
    response = MagicMock()
    response.status_code = 404
    client = MagicMock()
    client.__enter__.return_value = client
    client.get.side_effect = (httpx.HTTPStatusError
    (
        "failed",
        request=MagicMock(),
        response=response,
    ))

    (monkeypatch.setattr
    (
        "app.services.whois_service.httpx.Client",
        lambda **kwargs: client,
    ))
    result = collect_whois_raw_data("bob.com")
    assert result["error"] == "HTTP 404"


def test_whois_request_failed(monkeypatch):
    client = MagicMock()
    client.__enter__.return_value = client
    client.get.side_effect = (httpx.RequestError
    (
        "failed",
        request=MagicMock(),
    ))

    (monkeypatch.setattr
    (
        "app.services.whois_service.httpx.Client",
        lambda **kwargs: client,
    ))

    result = collect_whois_raw_data("tim.com")

    assert result["error"] == "failed"