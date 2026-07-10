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
    