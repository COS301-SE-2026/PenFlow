import pytest
from fastapi import HTTPException

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