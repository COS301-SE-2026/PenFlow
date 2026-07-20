import pytest
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
