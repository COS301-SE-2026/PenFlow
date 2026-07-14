from unittest.mock import MagicMock, patch

import dns.resolver
import pytest
from fastapi import HTTPException

from app.services.verification_service import VerificationService


def test_generate_txt_token():
    token = VerificationService.generate_txt_token()

    assert token.startswith("penflow-verification=")
    assert len(token) > 30

@patch("app.services.verification_service.dns.resolver.resolve")
def test_verify_dns_txt_success(mock_resolve):
    mock_answer = MagicMock()
    mock_answer.strings = [b"penflow-verification=12345"]
    mock_resolve.return_value = [mock_answer]

    result = VerificationService.verify_dns_txt("jeandre.co", "penflow-verification=12345")

    assert result is True
    mock_resolve.assert_called_once_with("jeandre.co", "TXT")

@patch("app.services.verification_service.dns.resolver.resolve")
def test_verify_dns_txt_failure_wrong_token(mock_resolve):
    mock_answer = MagicMock()
    mock_answer.strings = [b"google-site-verification=wrong"]
    mock_resolve.return_value = [mock_answer]

    result = VerificationService.verify_dns_txt("jeandre.co", "penflow-verification=12345")

    assert result is False

@patch("app.services.verification_service.dns.resolver.resolve")
def test_verify_dns_txt_nxdomain(mock_resolve):
    mock_resolve.side_effect = dns.resolver.NXDOMAIN

    with pytest.raises(HTTPException) as exc_info:
        VerificationService.verify_dns_txt("not-a-real-domain.xyz", "token")

    assert exc_info.value.status_code == 404
    assert "does not exist" in exc_info.value.detail
