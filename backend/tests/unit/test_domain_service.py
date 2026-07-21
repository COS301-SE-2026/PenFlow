from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.verified_domain import DomainVerificationStatus
from app.schemas.domain import DomainItem, DomainSortField, SortOrder
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


@pytest.mark.asyncio
@patch("app.services.domain_service.DomainRepository.create_rec", new_callable=AsyncMock)
@patch("app.services.domain_service.VerificationService.generate_txt_token")
@patch("app.services.domain_service.DomainRepository.get_by_domain", new_callable=AsyncMock)
async def test_add_domain_duplicate(mock_get_domain, mock_gen_token, mock_create_domain):
    db = AsyncMock()
    user_id = uuid4()

    existing_domain = SimpleNamespace(
        id = uuid4(),
        domain = "test.com",
        user_id = user_id,
        status = DomainVerificationStatus.PENDING,
    )

    mock_get_domain.return_value = existing_domain

    with pytest.raises(HTTPException) as excep:
        await DomainService.add_domain(
            db,
            domain = "https://test.com",
            user_id = user_id,
        )

    assert excep.value.status_code == 409
    assert excep.value.detail == "This domain has already been added"

    mock_get_domain.assert_awaited_once_with(
        db,
        domain = "test.com",
        user_id = user_id,
    )

    mock_gen_token.assert_not_called()
    mock_create_domain.assert_not_awaited()


@pytest.mark.asyncio
@patch.object(DomainItem, "model_validate")
@patch("app.services.domain_service.DomainRepository.get_status_counts", new_callable=AsyncMock)
@patch("app.services.domain_service.DomainRepository.list_domains", new_callable=AsyncMock)
async def test_list_domains(mock_list_domains, mock_status_counts, mock_model_validate):
    db = AsyncMock()
    user_id = uuid4()

    domain_one = SimpleNamespace(
        id = uuid4(),
        domain = "one.test.com",
        status = DomainVerificationStatus.VERIFIED,
    )

    domain_two = SimpleNamespace(
        id = uuid4(),
        domain = "two.test.com",
        status = DomainVerificationStatus.PENDING,
    )

    first_item = DomainItem.model_construct(
        id = domain_one.id,
        domain = domain_one.domain,
        status = domain_one.status,
    )

    second_item = DomainItem.model_construct(
        id = domain_two.id,
        domain = domain_two.domain,
        status = domain_two.status,
    )

    mock_list_domains.return_value = ([domain_one, domain_two], 5)

    mock_status_counts.return_value = {
        DomainVerificationStatus.PENDING: 2,
        DomainVerificationStatus.VERIFIED: 3,
        DomainVerificationStatus.FAILED: 1,
        DomainVerificationStatus.EXPIRED: 1,
    }

    mock_model_validate.side_effect = [
        first_item,
        second_item,
    ]

    result = await DomainService.list_domains(
        db,
        user_id = user_id,
        verification_status = DomainVerificationStatus.VERIFIED,
        search = "test",
        sort = DomainSortField.CREATED_AT,
        order = SortOrder.DESC,
        limit = 2,
        offset = 0,
    )

    mock_list_domains.assert_awaited_once_with(
        db,
        user_id = user_id,
        verification_status = DomainVerificationStatus.VERIFIED,
        search = "test",
        sort = DomainSortField.CREATED_AT,
        order = SortOrder.DESC,
        limit = 2,
        offset = 0,
    )

    mock_status_counts.assert_awaited_once_with(
        db,
        user_id = user_id,
    )

    assert mock_model_validate.call_count == 2
    mock_model_validate.assert_any_call(domain_one)
    mock_model_validate.assert_any_call(domain_two)

    assert result.items == [
        first_item,
        second_item,
    ]

    assert result.counts.all == 7
    assert result.counts.pending == 2
    assert result.counts.verified == 3
    assert result.counts.failed == 1
    assert result.counts.expired == 1

    assert result.pagination.total == 5
    assert result.pagination.limit == 2
    assert result.pagination.offset == 0
    assert result.pagination.has_more is True


@pytest.mark.asyncio
@patch.object(DomainItem, "model_validate")
@patch("app.services.domain_service.DomainRepository.get_status_counts", new_callable=AsyncMock)
@patch("app.services.domain_service.DomainRepository.list_domains", new_callable=AsyncMock)
async def test_list_domains_final_page(mock_list_domains, mock_status_counts, mock_model_validate):
    db = AsyncMock()
    user_id = uuid4()

    domain = SimpleNamespace(
        id = uuid4(),
        domain = "test.com",
        status = DomainVerificationStatus.PENDING,
    )


    item = DomainItem.model_construct(
        id = domain.id,
        domain = domain.domain,
        status = domain.status,
    )

    mock_list_domains.return_value = ([domain], 5)

    mock_status_counts.return_value = {
        DomainVerificationStatus.PENDING: 5,
        DomainVerificationStatus.VERIFIED: 0,
        DomainVerificationStatus.FAILED: 0,
        DomainVerificationStatus.EXPIRED: 0,
    }

    mock_model_validate.return_value = item

    result = await DomainService.list_domains(
        db,
        user_id = user_id,
        verification_status = None,
        search = None,
        sort = DomainSortField.CREATED_AT,
        order = SortOrder.DESC,
        limit = 2,
        offset = 4,
    )

    assert result.pagination.total == 5
    assert result.pagination.limit == 2
    assert result.pagination.offset == 4
    assert result.pagination.has_more is False


@pytest.mark.asyncio
@patch("app.services.domain_service.VerificationService.verify_dns_txt", new_callable=AsyncMock)
@patch("app.services.domain_service.DomainRepository.get_by_id", new_callable=AsyncMock)
async def test_verify_domain_not_found(mock_get_domain, mock_verify_dns):
    db = AsyncMock()
    domain_id = uuid4()
    user_id = uuid4()

    mock_get_domain.return_value = None

    with pytest.raises(HTTPException) as excep:
        await DomainService.verify_domain(
            db,
            domain_id = domain_id,
            user_id = user_id,
        )

    assert excep.value.status_code == 404
    assert excep.value.detail == "Domain record was not found"

    mock_get_domain.assert_awaited_once_with(
        db,
        domain_id = domain_id,
        user_id = user_id,
    )

    mock_verify_dns.assert_not_awaited()