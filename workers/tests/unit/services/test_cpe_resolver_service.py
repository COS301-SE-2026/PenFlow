import pytest

from app.services.cpe_resolver_service import (
    CPEResolverService,
    run_cpe_resolution,
)


@pytest.fixture
def software_inventory():
    return \
    [
        {
            "vendor": "apache",
            "product": "tomcat",
            "version": "10.1.0",
        },
        {
            "vendor": "nginx",
            "product": "nginx",
            "version": None,
        },
    ]

#need to be able to add cpe
def test_run_adds_cpe_strings(software_inventory):
    service = CPEResolverService(software_inventory)

    result = service.run()

    assert len(result) == 2

    assert \
    (
        result[0]["cpe"]
        == "cpe:2.3:a:apache:tomcat:10.1.0:*:*:*:*:*:*:*"
    )

    assert \
    (
        result[1]["cpe"]
        == "cpe:2.3:a:nginx:nginx:*:*:*:*:*:*:*:*"
    )

def test_run_cpe_resolution_wrapper(software_inventory):
    result = run_cpe_resolution(software_inventory)

    assert len(result) == 2
    assert "cpe" in result[0]