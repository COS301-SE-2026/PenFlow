from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.verified_domain import DomainVerificationStatus
from app.services.domain_service import DomainService


@pytest.mark.parametrize(
    ("domain", "expected"),
    [
        ("test.com", "test.com"),
        (" TEST.COM ", "test.com"),
        ("https://test.com", "test.com"),
        ("http://test.com", "test.com"),
        ("test.com.", "test.com"),
        ("subdomain.test.com", "subdomain.test.com"),
    ],
)

def test_strip_domain(domain, expected):
    result = DomainService.strip_domain(domain)

    assert result == expected


@pytest.mark.parametrize(
    "domain",
    [
        "",
        " ",
        "https://",
        "http://",
    ],
)

def test_strip_domain_invalid(domain):
    with pytest.raises(HTTPException) as excep:
        DomainService.strip_domain(domain)

    assert excep.value.status_code == 422
    assert excep.value.detail == "A valid domain is needed"


@pytest.mark.asyncio
@patch("app.services.domain_service.DomainRepository.create_rec", new_callable=AsyncMock)
@patch("app.services.domain_service.VerificationService.generate_txt_token")
@patch("app.services.domain_service.DomainRepository.get_by_domain", new_callable=AsyncMock)
async def test_add_domain(mock_get_domain, mock_gen_token, mock_create_domain):
    db = AsyncMock()
    user_id = uuid4()
    domain_id = uuid4()

    created_domain = SimpleNamespace(
        id = domain_id,
        domain = "test.com",
        user_id = user_id,
        verification_token = "penflow-verification=test-token",
        status = DomainVerificationStatus.PENDING,
    )

    mock_get_domain.return_value = None
    mock_gen_token.return_value = "penflow-verification=test-token"
    mock_create_domain.return_value = created_domain

    result = await DomainService.add_domain(
        db,
        domain = " HTTPS://TEST.COM/ ",
        user_id = user_id,
    )

    mock_get_domain.assert_awaited_once_with(
        db,
        domain = "test.com",
        user_id = user_id,
    )

    mock_gen_token.assert_called_once_with()

    mock_create_domain.assert_awaited_once_with(
        db,
        domain = "test.com",
        verification_token = "penflow-verification=test-token",
        user_id = user_id,
    )

    assert result == created_domain