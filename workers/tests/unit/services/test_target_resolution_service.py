from unittest.mock import MagicMock, patch
import dns.exception
import dns.resolver
from app.services.target_resolution_service import resolve_target_ips

def create_mock_dns_answer(ip_records: list[str]) -> MagicMock:
    """
    Creating a fake response that includes ip records
    """

    records = []
    for ip in ip_records:
        record = MagicMock()
        record.to_text.return_value = ip
        records.append(record)
    answer = MagicMock()
    answer.__iter__.return_value = records
    return answer


#Happy path

# Happy Path [IPv4 and IPv6 found]
@patch("app.services.target_resolution_service.dns.resolver.Resolver.resolve")
def test_resolve_target_ips_success(mock_resolve):
    """
    Returns IPv4 and IPv6 as we would expect from any given domain we may test
    """

    def side_effect(domain, record_type):
        #ipv 4
        if record_type == "A":
            return create_mock_dns_answer([
                "192.168.1.1",
                "192.168.1.2",
            ])

        #ipv6
        if record_type == "AAAA":
            return create_mock_dns_answer([
                "2001:0df8:00f2::06ee:0000:0f11",
            ])

    mock_resolve.side_effect = side_effect

    result = resolve_target_ips("hackerone.com")

    assert result == {
        "ipv4": [
            "192.168.1.1",
            "192.168.1.2",
        ],
        "ipv6": [
            "2001:0df8:00f2::06ee:0000:0f11",
        ],
    }

    assert mock_resolve.call_count == 2


# Happy Path [IPv4 only]
@patch("app.services.target_resolution_service.dns.resolver.Resolver.resolve")
def test_resolve_target_ips_ipv4_only(mock_resolve):
    """
    Returning only the ipv4 results cause either ipv6 doesnt exist or fails
    """

    def side_effect(domain, record_type):
        if record_type == "A":
            return create_mock_dns_answer([
                "192.168.1.1",
            ])

        raise dns.resolver.NoAnswer

    mock_resolve.side_effect = side_effect

    result = resolve_target_ips("hackerone.com")

    assert result == {
        "ipv4": [
            "192.168.1.1",
        ],
        "ipv6": [],
    }


#Sad paths

# Sad Path [NXDOMAIN]
@patch("app.services.target_resolution_service.dns.resolver.Resolver.resolve")
def test_resolve_target_ips_domain_not_found(mock_resolve):
    """
    Returns a fully empty list beacuse the domain doesnt exist and thus we cannot resolve ips from it.
    """

    mock_resolve.side_effect = dns.resolver.NXDOMAIN

    result = resolve_target_ips("missing.com")

    assert result == {
        "ipv4": [],
        "ipv6": [],
    }


# Sad Path 2 [Timeout]

@patch("app.services.target_resolution_service.dns.resolver.Resolver.resolve")
def test_resolve_target_ips_timeout(mock_resolve):
    """
    Returns an empty list when we have a dns timeout issue from the polling taking to long to give us the desired result
    """

    mock_resolve.side_effect = dns.exception.Timeout

    result = resolve_target_ips("slow.com")

    assert result == {
        "ipv4": [],
        "ipv6": [],
    }
