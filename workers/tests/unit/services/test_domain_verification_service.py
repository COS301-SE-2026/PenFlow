from unittest.mock import MagicMock, patch
import dns.exception
import dns.resolver
from app.services.domain_verification_service import verify_txt_record

def create_mock_dns_answer(txt_records: list[str]) -> MagicMock:
    """
    Creates a fake dnspython response containing TXT records.
    """

    records = []
    for txt in txt_records:
        record = MagicMock()
        record.to_text.return_value = f'"{txt}"'
        records.append(record)
    answer = MagicMock()
    answer.__iter__.return_value = records
    return answer


# 1 happy path [Token found]

@patch("app.services.domain_verification_service.dns.resolver.resolve")
def test_verify_txt_record_token_found(mock_resolve):
    """
    Returns True when the expected verification token exists.
    """

    domain = "hackerone.com"
    token = "penflow-verify=abc123"
    mock_resolve.return_value = create_mock_dns_answer([
        "v=spf1 include:_spf.google.com ~all",
        token,
    ])
    result = verify_txt_record(domain, token)
    assert result is True
    mock_resolve.assert_called_once_with(domain, "TXT")



# 4 verification failure cases
# [Token not found] [DNS timeout] [Domain not found] [Unexpected error]

#Token not foud
@patch("app.services.domain_verification_service.dns.resolver.resolve")
def test_verify_txt_record_token_not_found(mock_resolve):
    """
    Returns False when TXT records exist but none match.
    """
    domain = "hackerone.com"
    token = "penflow-verify=abc123"
    mock_resolve.return_value = create_mock_dns_answer([
        "google-site-verification=test",
        "v=spf1 include:_spf.google.com ~all",
    ])
    result = verify_txt_record(domain, token)
    assert result is False
    mock_resolve.assert_called_once_with(domain, "TXT")

#domain not found
@patch("app.services.domain_verification_service.dns.resolver.resolve")
def test_verify_txt_record_domain_not_found(mock_resolve):
    """
    Returns False when the domain does not exist.
    """

    domain = "babboonVoid.com"
    token = "token"
    mock_resolve.side_effect = dns.resolver.NXDOMAIN
    result = verify_txt_record(domain, token)
    assert result is False
    mock_resolve.assert_called_once_with(domain, "TXT")

#DNS Timeout
@patch("app.services.domain_verification_service.dns.resolver.resolve")
def test_verify_txt_record_timeout(mock_resolve):
    """
    Returns False when the DNS lookup times out.
    """

    domain = "hackerone.com"
    token = "token"
    mock_resolve.side_effect = dns.exception.Timeout
    result = verify_txt_record(domain, token)
    assert result is False
    mock_resolve.assert_called_once_with(domain, "TXT")

#unexpected error
@patch("app.services.domain_verification_service.dns.resolver.resolve")
def test_verify_txt_record_unexpected_exception(mock_resolve):
    """
    Returns False when an unexpected exception occurs.
    """

    domain = "hackerone.com"
    token = "token"
    mock_resolve.side_effect = Exception("Unexpected DNS failure")
    result = verify_txt_record(domain, token)
    assert result is False
    mock_resolve.assert_called_once_with(domain, "TXT")