from unittest.mock import MagicMock, mock_open, patch

import pytest

from app.services.fingerprinting_service import FingerprintingService


@pytest.fixture
def base_service():
    return FingerprintingService\
    (
        target_url="https://hackerone.com",
    )

#can we collect http data correctly, do we build the cache properly
@patch("app.services.fingerprinting_service.requests.get")
def test_collect_http_data_success(mock_get, base_service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.url = "https://hackerone.com/"
    mock_response.headers = \
    {
        "Server": "nginx/1.18.0",
        "X-Powered-By": "PHP/7.4",
    }

    mock_cookies = MagicMock()
    mock_cookies.get_dict.return_value = \
    {
        "PHPSESSID": "12345",
    }

    mock_response.cookies = mock_cookies

    mock_response.text = """
    <html>
        <head>
            <title>Test Page</title>
            <meta name="generator" content="WordPress 5.8" />
            <link rel="stylesheet" href="style.css" />
            <script src="jquery.js"></script>
        </head>
    </html>
    """

    mock_get.return_value = mock_response
    base_service.collect_http_data()

    assert base_service.cache["status_code"] == 200
    assert base_service.cache["headers"]["server"] == "nginx/1.18.0"
    assert base_service.cache["cookies"]["phpsessid"] == "12345"
    assert base_service.cache["title"] == "test page"
    assert len(base_service.cache["meta_tags"]) == 1
    assert base_service.cache["scripts"] == ["jquery.js"]
    assert base_service.cache["links"] == ["style.css"]


@patch("app.services.fingerprinting_service.requests.get")
def test_collect_http_data_exception(mock_get, base_service):
    mock_get.side_effect = Exception("Connection timed out")

    base_service.collect_http_data()

    assert base_service.cache["status_code"] == 0
    assert base_service.cache["headers"] == {}


def test_extract_version_header(base_service):
    base_service.cache["headers"] = \
    {
        "server": "apache/2.4.41 (ubuntu)",
    }

    rules = \
    {
        "version_extractors":
        [
            {
                "type": "header",
                "target": "server",
                "regex": r"apache/([\d\.]+)",
            }
        ]
    }

    result = base_service._extract_version(rules)

    assert result == "2.4.41"

#do we get version
def test_extract_version_meta(base_service):
    base_service.cache["meta_tags"] = \
    [
        {
            "name": "generator",
            "content": "Joomla! 3.9",
        }
    ]

    rules = \
    {
        "version_extractors":
        [
            {
                "type": "meta",
                "target": "generator",
                "regex": r"joomla!\s([\d\.]+)",
            }
        ]
    }

    result = base_service._extract_version(rules)

    assert result == "3.9"


def test_extract_version_none(base_service):
    base_service.cache["headers"] = \
    {
        "server": "apache",
    }

    rules = \
    {
        "version_extractors":
        [
            {
                "type": "header",
                "target": "server",
                "regex": r"apache/([\d\.]+)",
            }
        ]
    }

    result = base_service._extract_version(rules)

    assert result is None

def test_merge_nmap_existing(base_service):
    base_service.discovered["f5_nginx"] = \
    {
        "category": "web_server",
        "vendor": "f5",
        "product": "nginx",
        "version": None,
        "evidence_score": 60,
        "sources": ["header"],
    }

    base_service.nmap_data = \
    {
        "ports":
        [
            {
                "product": "nginx",
                "version": "1.18.0",
            }
        ]
    }

    base_service.merge_with_nmap()

    software = base_service.discovered["f5_nginx"]

    assert software["version"] == "1.18.0"
    assert software["evidence_score"] == 85
    assert "nmap" in software["sources"]


def test_merge_nmap_new(base_service):
    base_service.nmap_data = \
    {
        "ports":
        [
            {
                "product": "OpenSSH",
                "version": "8.2p1",
            }
        ]
    }

    base_service.merge_with_nmap()

    software = base_service.discovered["unknown_openssh"]

    assert software["category"] == "service"
    assert software["product"] == "openssh"
    assert software["version"] == "8.2p1"
    assert software["evidence_score"] == 85


def test_merge_tls_cloudflare(base_service):
    base_service.tls_data = \
    {
        "targets":
        [
            {
                "certificate":
                {
                    "issuer":
                    {
                        "organizationName": "Cloudflare, Inc.",
                    }
                }
            }
        ]
    }

    base_service.merge_with_tls()

    software = base_service.discovered["cloudflare_cloudflare"]

    assert software["category"] == "cdn"
    assert software["evidence_score"] == 60


def test_merge_tls_exception(base_service):
    base_service.tls_data = None

    base_service.merge_with_tls()

    assert "cloudflare_cloudflare" not in base_service.discovered


def test_export_confidence_calculation(base_service):
    base_service.discovered["vendor1_prod1"] = \
    {
        "category": "test",
        "vendor": "vendor1",
        "product": "prod1",
        "version": "1",
        "evidence_score": 95,
        "sources": [],
    }

    base_service.discovered["vendor2_prod2"] = \
    {
        "category": "test",
        "vendor": "vendor2",
        "product": "prod2",
        "version": "1",
        "evidence_score": 75,
        "sources": [],
    }

    base_service.discovered["vendor3_prod3"] = \
    {
        "category": "test",
        "vendor": "vendor3",
        "product": "prod3",
        "version": "1",
        "evidence_score": 20,
        "sources": [],
    }

    result = base_service.export()

    for software in result["fingerprint"]["software"]:
        if software["product"] == "prod1":
            assert software["confidence"] == "high"

        elif software["product"] == "prod2":
            assert software["confidence"] == "medium"

        else:
            assert software["confidence"] == "low"


def test_log_unmatched_tech(base_service):
    base_service.cache["headers"]["server"] = "unimatrix-server-1701"

    base_service._log_unmatched_tech()

    assert \
    (
        "unimatrix-server-1701"
        in base_service.telemetry["unknown_server_strings"]
    )


@patch("app.services.fingerprinting_service.Path.open", new_callable=mock_open)
def test_write_telemetry_file(mock_file_open, base_service):
    base_service.telemetry["unknown_server_strings"] = \
    [
        "unimatrix-server-1701",
    ]

    base_service.telemetry["unknown_headers"] = \
    [
        "x-custom-tracking",
    ]

    base_service._write_telemetry_file()

    handle = mock_file_open()

    handle.write.assert_any_call("[unknown_server_strings]\n")
    handle.write.assert_any_call("  - unimatrix-server-1701\n")
    handle.write.assert_any_call("[unknown_headers]\n")


@patch("app.services.fingerprinting_service.Path.open", new_callable=mock_open)
@patch.object(FingerprintingService, "export")
@patch.object(FingerprintingService, "merge_with_tls")
@patch.object(FingerprintingService, "merge_with_nmap")
@patch.object(FingerprintingService, "_evaluate_signatures")
@patch.object(FingerprintingService, "collect_http_data")
def test_run_orchestration\
(
    mock_collect,
    mock_evaluate,
    mock_merge_nmap,
    mock_merge_tls,
    mock_export,
    mock_file_open,
    base_service,
):
    mock_export.return_value = \
    {
        "status": "success",
    }

    result = base_service.run()

    mock_collect.assert_called_once()
    assert mock_evaluate.call_count == 7
    mock_merge_nmap.assert_called_once()
    mock_merge_tls.assert_called_once()
    mock_export.assert_called_once()

    assert result == {"status": "success"}