from unittest.mock import MagicMock, patch

import httpx

from app.tasks.hibp_tasks import run_hibp

#live happy path
@patch("app.services.hibp_service.httpx.Client.get")
@patch("app.services.hibp_service.HIBP_API_KEY", "Real_Cos_301_FUN")
@patch("app.services.hibp_service.SCAN_MODE", "LIVE")
def test_hibp_live_happy_path(mock_get):
    """Test that a real key triggers a live HTTP request and parses the breach list."""
    #fake the live api response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"Name": "LinkedIn", "Title": "LinkedIn"},
        {"Name": "Adobe", "Title": "Adobe"},
        {"Name": "Dropbox", "Title": "Dropbox"},
    ]
    mock_get.return_value = mock_response

    #execution
    result = run_hibp("scan-123", "acorns.com")

    #assertions
    assert result["scan_id"] == "scan-123"
    assert result["status"] == "completed"
    assert mock_get.called #proves it hit the internet

    breach_data = result["raw_result"]["breach_data"]

    assert breach_data["provider"] == "HaveIBeenPwned"
    assert breach_data["pwned_accounts_count"] == 3
    assert "LinkedIn" in breach_data["known_breaches"]
    assert len(result["findings"]) == 1 #should generate a high-severity finding


#sad path for api outage
@patch("app.services.hibp_service.httpx.Client.get")
@patch("app.services.hibp_service.HIBP_API_KEY", "Real_Cos_301_FUN")
@patch("app.services.hibp_service.SCAN_MODE", "LIVE")
def test_hibp_live_api_failure(mock_get):
    """Test that an HTTP error gracefully degrades into a failed status."""
    #force a network crash
    mock_get.side_effect = httpx.HTTPError("HIBP API Down")
    #execution
    result = run_hibp("scan-123", "acorns.com")

    #expect clean failure dict
    assert result["status"] == "failed"
    assert "error" in result["raw_result"]

#mock fallback path
@patch("app.services.hibp_service.httpx.Client.get")
@patch("app.services.hibp_service.HIBP_API_KEY", "fake_key_1234")
@patch("app.services.hibp_service.SCAN_MODE", "LIVE")
def test_hibp_fallback_to_mock(mock_get):
    """Test that a fake key safely bypasses the internet and loads local mock data."""
    #execution
    result = run_hibp("scan-123", "acorns.com")

    assert result["scan_id"] == "scan-123"
    #key is fake so it should never attempt a network request
    assert not mock_get.called
    assert result["status"] == "completed"

    assert "breach_data" in result["raw_result"]
    #mock data should load safely
    assert "pwned_accounts_count" in result["raw_result"]["breach_data"]