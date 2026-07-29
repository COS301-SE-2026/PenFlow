from unittest.mock import AsyncMock, MagicMock, patch

import dns.resolver
import pytest

from app.models.verified_domain import DomainVerificationCode
from app.services.verification_service import VerificationService


def test_generate_txt_token():
    token = VerificationService.generate_txt_token()

    assert token.startswith("penflow-verification=")
    assert len(token) > 30


@pytest.mark.asyncio
@patch("app.services.verification_service.dns.asyncresolver.resolve", new_callable=AsyncMock)
async def test_verify_dns_txt_success(mock_resolve):
    mock_answer = MagicMock()
    mock_answer.strings = [b"penflow-verification=12345"]
    mock_resolve.return_value = [mock_answer]

    result = await VerificationService.verify_dns_txt("jeandre.co", "penflow-verification=12345")

    assert result == DomainVerificationCode.VERIFIED
    mock_resolve.assert_called_once_with("jeandre.co", "TXT", lifetime=5.0)


@pytest.mark.asyncio
@patch("app.services.verification_service.dns.asyncresolver.resolve", new_callable=AsyncMock)
async def test_verify_dns_txt_failure_wrong_token(mock_resolve):
    mock_answer = MagicMock()
    mock_answer.strings = [b"google-site-verification=wrong"]
    mock_resolve.return_value = [mock_answer]

    result = await VerificationService.verify_dns_txt("jeandre.co", "penflow-verification=12345")

    assert result == DomainVerificationCode.TOKEN_MISMATCH


@pytest.mark.asyncio
@patch("app.services.verification_service.dns.asyncresolver.resolve")
async def test_verify_dns_txt_nxdomain(mock_resolve):
    mock_resolve.side_effect = dns.resolver.NXDOMAIN

    result = await VerificationService.verify_dns_txt(
        "fake-domain.com",
        "nothing token",
    )

    assert result == DomainVerificationCode.RECORD_NOT_FOUND
