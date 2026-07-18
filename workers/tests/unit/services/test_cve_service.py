from unittest.mock import MagicMock, patch

import pytest

from app.services.cve_service import (
    CVEService,
    run_cve_scan,
)


#mock architecture we find in fingerprint and cpe resolver
@pytest.fixture
def resolved_inventory():
    return \
    [
        {
            "vendor": "apache",
            "product": "tomcat",
            "version": "10.1.0",
            "confidence": "high",
            "cpe": "cpe:2.3:a:apache:tomcat:10.1.0:*:*:*:*:*:*:*",
        }
    ]

#do we skip what we are unsure of
def test_skip_low_confidence():
    service = CVEService\
    (
        [
            {
                "confidence": "low",
                "cpe": "cpe:2.3:a:test:test:1:*:*:*:*:*:*:*",
            }
        ]
    )

    assert service.run() == []

#high should run but no cpe means no query info
def test_skip_missing_cpe():
    service = CVEService\
    (
        [
            {
                "confidence": "high",
            }
        ]
    )

    assert service.run() == []

#wildcard return entire NVD list, we do not want wildcards
#no version means we cant query otherwise we will get the wildcard
def test_skip_wildcard_version():
    service = CVEService\
    (
        [
            {
                "confidence": "high",
                "product": "nginx",
                "cpe": "cpe:2.3:a:nginx:nginx:*:*:*:*:*:*:*:*",
            }
        ]
    )

    assert service.run() == []

def test_deduplicate():
    service = CVEService([])

    service.vulnerabilities = \
    [
        {
            "cve_id": "CVE-123",
            "affected_software": "apache",
        },
        {
            "cve_id": "CVE-123",
            "affected_software": "apache",
        },
        {
            "cve_id": "CVE-456",
            "affected_software": "apache",
        },
    ]

    result = service._deduplicate()

    assert len(result) == 2

#can we succesfully query with the correct info
@patch("app.services.cve_service.requests.get")
def test_lookup_nvd_success(mock_get, resolved_inventory):
    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_response.json.return_value = \
    {
        "vulnerabilities":
        [
            {
                "cve":
                {
                    "id": "CVE-2025-0001",
                    "descriptions":
                    [
                        {
                            "value": "Example vulnerability.",
                        }
                    ],
                    "metrics":
                    {
                        "cvssMetricV31":
                        [
                            {
                                "cvssData":
                                {
                                    "baseSeverity": "HIGH",
                                    "baseScore": 9.8,
                                }
                            }
                        ]
                    },
                    "configurations":
                    [
                        {
                            "nodes":
                            [
                                {
                                    "cpeMatch":
                                    [
                                        {
                                            "vulnerable": True,
                                            "criteria":
                                            "cpe:2.3:a:apache:tomcat:10.1.0:*:*:*:*:*:*:*",
                                        }
                                    ]
                                }
                            ]
                        }
                    ],
                }
            }
        ]
    }

    mock_get.return_value = mock_response

    service = CVEService(resolved_inventory)

    result = service._lookup_nvd\
    (
        resolved_inventory[0]["cpe"],
        resolved_inventory[0],
    )

    assert len(result) == 1
    assert result[0]["cve_id"] == "CVE-2025-0001"
    assert result[0]["severity"] == "HIGH"


@patch("app.services.cve_service.requests.get")
def test_lookup_nvd_exception(mock_get, resolved_inventory):
    mock_get.side_effect = Exception("Connection failed")

    service = CVEService(resolved_inventory)

    result = service._lookup_nvd\
    (
        resolved_inventory[0]["cpe"],
        resolved_inventory[0],
    )

    assert result == []


@patch.object(CVEService, "run")
def test_run_cve_scan_wrapper(mock_run, resolved_inventory):
    mock_run.return_value = \
    [
        {
            "cve_id": "CVE-2025-0001",
        }
    ]

    result = run_cve_scan(resolved_inventory)

    assert len(result) == 1
    assert result[0]["cve_id"] == "CVE-2025-0001"