from unittest.mock import MagicMock, patch
import requests

from app.services.http_security_service import run_http_security_scan


def create_mock_response\
(
    status_code: int = 200,
    headers: dict | None = None,
):
    """
    Creates a fake HTTP response object.
    """

    response = MagicMock()
    response.status_code = status_code
    response.headers = headers or {}
    return response

##Happy Paths [HTTP]
@patch("app.services.http_security_service.requests.get")
def test_http_endpoint(mock_get):
    """
    Successfully scan for http.
    """

    mock_get.return_value = create_mock_response()

    result = run_http_security_scan\
    (
        hostname="hackerone.com",
        ip_address="1.1.1.1",
        ports=[
            {
                "port": 80,
                "service": "http",
            }
        ],
    )

    mock_get.assert_called_once_with\
    (
        "http://hackerone.com",
        timeout=5,
        verify=False,
        allow_redirects=True,
    )

    assert len(result["targets"]) == 1

#[HTTPS]
@patch("app.services.http_security_service.requests.get")
def test_https_endpoint(mock_get):
    """
    Successfully scan for http and extracts headers.
    """

    mock_get.return_value = create_mock_response\
    (
        headers=\
        {
            "Strict-Transport-Security": "max-age=31536000",
            "Content-Security-Policy": "default-src 'self'",
            "Server": "nginx",
            "X-Powered-By": "PHP",
        }
    )

    result = run_http_security_scan\
    (
        hostname="hackerone.com",
        ip_address="1.1.1.1",
        ports=[
            {
                "port": 443,
                "service": "https",
            }
        ],
    )

    mock_get.assert_called_once_with\
    (
        "https://hackerone.com",
        timeout=5,
        verify=False,
        allow_redirects=True,
    )

    target = result["targets"][0]

    assert target["server"] == "nginx"
    assert target["powered_by"] == "PHP"
    assert \
    (
        target["security_headers"]["strict_transport_security"]
        == "max-age=31536000"
    )
    assert \
    (
        target["security_headers"]["content_security_policy"]
        == "default-src 'self'"
    )

#[Multiple HTTP Endpoints]
@patch("app.services.http_security_service.requests.get")
def test_multiple_http_endpoints(mock_get):
    """
    Successfully scans multiple HTTP.
    """

    mock_get.return_value = create_mock_response()

    result = run_http_security_scan\
    (
        hostname="hackerone.com",
        ip_address="1.1.1.1",
        ports=[
            {
                "port": 80,
                "service": "http",
            },
            {
                "port": 443,
                "service": "https",
            },
        ],
    )

    assert len(result["targets"]) == 2
    assert mock_get.call_count == 2



##Sad Paths [Ignore Non-HTTP]
@patch("app.services.http_security_service.requests.get")
def test_non_http_ports_are_ignored(mock_get):
    """
    Ignores services unrelated to HTTP.
    """

    result = run_http_security_scan\
    (
        hostname="hackerone.com",
        ip_address="1.1.1.1",
        ports=[
            {
                "port": 22,
                "service": "ssh",
            },
            {
                "port": 3306,
                "service": "mysql",
            },
        ],
    )

    assert result["targets"] == []
    mock_get.assert_not_called()

#[Connection Failure]
@patch("app.services.http_security_service.requests.get")
def test_connection_failure(mock_get):
    """
    Returns no targets when the HTTP request fails.
    """

    mock_get.side_effect = requests.RequestException\
    (
        "Connection failed"
    )

    result = run_http_security_scan\
    (
        hostname="hackerone.com",
        ip_address="1.1.1.1",
        ports=[
            {
                "port": 80,
                "service": "http",
            }
        ],
    )

    assert result["targets"] == []