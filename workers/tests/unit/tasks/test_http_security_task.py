from unittest.mock import patch

from app.tasks.http_security_task import run_http_security_scan_task


##Happy Paths [Successful Scan]
@patch("app.tasks.http_security_task.send_source_callback")
@patch("app.tasks.http_security_task.run_http_security_scan")
def test_successful_scan(mock_scan, mock_callback):
    """
    Returns a completed scan result.
    """

    mock_scan.return_value = \
    {
        "targets": []
    }

    result = run_http_security_scan_task.run\
    (
        scan_id="scan123",
        hostname="hackerone.com",
        ip_address="1.1.1.1",
        ports=[],
    )

    assert result["status"] == "completed"
    assert result["findings"] == []

    mock_callback.assert_called_once()

#[Missing Security Headers]
@patch("app.tasks.http_security_task.send_source_callback")
@patch("app.tasks.http_security_task.run_http_security_scan")
def test_missing_security_headers(mock_scan, mock_callback):
    """
    Generates findings when important security headers are missing, so missing https for example.
    """

    mock_scan.return_value = \
    {
        "targets": [
            {
                "url": "https://hackerone.com",
                "scheme": "https",
                "port": 443,
                "status_code": 200,
                "security_headers": {},
            }
        ]
    }

    result = run_http_security_scan_task.run\
    (
        scan_id="scan123",
        hostname="hackerone.com",
        ip_address="1.1.1.1",
        ports=[],
    )

    titles = [finding["title"] for finding in result["findings"]]

    assert "Missing Content-Security-Policy" in titles
    assert "Missing Strict-Transport-Security" in titles


##Sad Paths [HTTP ignores HSTS]
@patch("app.tasks.http_security_task.send_source_callback")
@patch("app.tasks.http_security_task.run_http_security_scan")
def test_http_vs_hsts(mock_scan, mock_callback):
    """
    HTTP endpoints should not require HSTS.
    """

    mock_scan.return_value = \
    {
        "targets": [
            {
                "url": "http://hackerone.com",
                "protocol": "http",
                "security_headers": \
                {
                    "content_security_policy": "default-src 'self'",
                    "strict_transport_security": None,
                    "x_frame_options": "DENY",
                    "referrer_policy": "strict-origin",
                    "permissions_policy": "camera=()",
                    "x_content_type_options": "nosniff",
                },
            }
        ]
    }

    result = run_http_security_scan_task.run\
    (
        scan_id="scan123",
        hostname="hackerone.com",
        ip_address="1.1.1.1",
        ports=[],
    )

    titles = [finding["title"] for finding in result["findings"]]

    assert "Missing Strict-Transport-Security" not in titles

# [Scan Failure]
@patch("app.tasks.http_security_task.send_source_callback")
@patch("app.tasks.http_security_task.run_http_security_scan")
def test_scan_failure(mock_scan, mock_callback):
    """
    Returns a failed result.
    """

    mock_scan.side_effect = Exception\
    (
        "Unexpected HTTP failure"
    )

    result = run_http_security_scan_task.run\
    (
        scan_id="scan123",
        hostname="hackerone.com",
        ip_address="1.1.1.1",
        ports=[],
    )

    assert result["status"] == "failed"
    assert "Unexpected HTTP failure" in result["error_message"]

    mock_callback.assert_called_once()