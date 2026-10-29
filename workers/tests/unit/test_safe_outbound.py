from io import BytesIO
from unittest.mock import Mock

import pytest
import requests
from urllib3 import HTTPResponse

from app.utils import safe_outbound as outbound


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.1",
        "172.16.0.1",
        "192.168.0.1",
        "169.254.169.254",
        "100.64.0.1",
        "::1",
        "fc00::1",
        "fe80::1",
        "::ffff:127.0.0.1",
        "64:ff9b::7f00:1",
        "168.63.129.16",
    ],
)
def test_rejects_unsafe_addresses(address):
    with pytest.raises(outbound.UnsafeDestination):
        outbound.public_ip(address)


def test_rejects_mixed_dns_answers(monkeypatch):
    resolver = Mock()
    resolver.resolve.return_value = [
        Mock(to_text=lambda: "1.1.1.1"),
        Mock(to_text=lambda: "10.0.0.1"),
    ]

    monkeypatch.setattr(
        outbound.dns.resolver,
        "Resolver",
        lambda: resolver,
    )

    with pytest.raises(outbound.UnsafeDestination):
        outbound.resolve_public_host("example.com")


def test_redirect_cannot_reach_metadata(monkeypatch):
    response = requests.Response()
    response.status_code = 302
    response.headers["Location"] = (
        "http://169.254.169.254/latest/meta-data/"
    )

    def resolve(host, **kwargs):
        return [
            outbound.public_ip(
                "1.1.1.1"
                if host == "example.com"
                else host
            )
        ]

    fetch = Mock(return_value=response)

    monkeypatch.setattr(
        outbound,
        "resolve_public_host",
        resolve,
    )
    monkeypatch.setattr(outbound, "_fetch_ip", fetch)

    with pytest.raises(outbound.UnsafeDestination):
        outbound.safe_get("https://example.com")

    assert fetch.call_count == 1


def test_connection_uses_ip_and_preserves_hostname(monkeypatch):
    pool = Mock()
    pool.urlopen.return_value = HTTPResponse(
        body=BytesIO(b"hello"),
        status=200,
        preload_content=False,
    )

    factory = Mock(return_value=pool)

    monkeypatch.setattr(
        outbound.urllib3,
        "HTTPSConnectionPool",
        factory,
    )

    response = outbound._fetch_ip(
        "https://example.com:443/",
        "example.com",
        443,
        "1.1.1.1",
        5.0,
        True,
        100,
    )

    assert factory.call_args.args[:2] == ("1.1.1.1", 443)
    assert (
        factory.call_args.kwargs["server_hostname"]
        == "example.com"
    )
    assert (
        pool.urlopen.call_args.kwargs["headers"]["Host"]
        == "example.com"
    )
    assert pool.urlopen.call_args.kwargs["redirect"] is False
    assert response.content == b"hello"
    pool.close.assert_called_once()


def test_rejects_oversized_response(monkeypatch):
    pool = Mock()
    pool.urlopen.return_value = HTTPResponse(
        body=BytesIO(b"123456"),
        status=200,
        preload_content=False,
    )

    monkeypatch.setattr(
        outbound.urllib3,
        "HTTPConnectionPool",
        Mock(return_value=pool),
    )

    with pytest.raises(outbound.UnsafeDestination):
        outbound._fetch_ip(
            "http://example.com:80/",
            "example.com",
            80,
            "1.1.1.1",
            5.0,
            True,
            5,
        )

    pool.close.assert_called_once()


@pytest.mark.parametrize(
    ("destination", "allowed"),
    [
        ("www.example.com", True),
        ("example.com.evil.com", False),
        ("evil.com", False),
    ],
)
def test_authorised_redirect_scope(monkeypatch, destination, allowed):
    first = requests.Response()
    first.status_code = 302
    first.headers["Location"] = f"https://{destination}/"

    second = requests.Response()
    second.status_code = 200

    fetch = Mock(side_effect=[first, second])

    monkeypatch.setattr(outbound, "_fetch_ip", fetch)
    monkeypatch.setattr(
        outbound,
        "resolve_public_host",
        Mock(return_value=["1.1.1.1"]),
    )

    if allowed:
        result = outbound.safe_get(
            "https://example.com",
            allowed_domain="example.com",
        )

        assert result is second
        assert fetch.call_count == 2

    else:
        with pytest.raises(outbound.UnsafeDestination):
            outbound.safe_get(
                "https://example.com",
                allowed_domain="example.com",
            )

        assert fetch.call_count == 1