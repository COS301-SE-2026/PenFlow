from unittest.mock import MagicMock, patch

import httpx

from app.tasks.hunter_tasks import run_hunter


@patch("app.services.hunter_service.httpx.Client.get")
@patch("app.services.hunter_service.HUNTER_API_KEY", "a_real_key_301")
@patch("app.services.hunter_service.SCAN_MODE", "LIVE")
def test_hunter_live_happy_path(mock_get):
    """Test that a real key triggers a live HTTP request and parses correctly."""
    
    #fake the live api response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "pattern": "{first}.{last}",
            "emails": [
                {"value": "ceo@acorns.com", "type": "personal", "confidence": 99},
                {"value": "info@acorns.com", "type": "generic", "confidence": 80},
            ],
        }
    }
    mock_get.return_value = mock_response

    #execution
    result = run_hunter("scan-123", "acorns.com")

    #assertions
    assert result["scan_id"] == "scan-123"
    assert result["source_name"] == "hunter.io"
    assert result["status"] == "completed"
    assert mock_get.called #proves it hit the live internet block

    phishing_surface = result["raw_result"]["phishing_surface"]

    assert phishing_surface["provider"] == "Hunter.io"
    assert len(phishing_surface["public_emails_found"]) == 2
    assert len(result["findings"]) == 1 #should generate 1 finding for discovered emails


@patch("app.services.hunter_service.httpx.Client.get")
@patch("app.services.hunter_service.HUNTER_API_KEY", "a_real_key_301")
@patch("app.services.hunter_service.SCAN_MODE", "LIVE")
def test_hunter_live_api_failure(mock_get):
    """Test that an HTTP error gracefully degrades into a failed status."""
    #force a network crash
    mock_get.side_effect = httpx.HTTPError("Hunter API Down")

    #execution
    result = run_hunter("scan-123", "acorns.com")

    #expect a clean failure dict not a crash
    assert result["status"] == "failed"
    assert "error" in result["raw_result"]


@patch("app.services.hunter_service.httpx.Client.get")
@patch("app.services.hunter_service.HUNTER_API_KEY", "fake_key_1234")
@patch("app.services.hunter_service.SCAN_MODE", "LIVE") #force live mode to test fake key trigger
def test_hunter_fallback_to_mock(mock_get):
    #execution
    result = run_hunter("scan-123", "acorns.com")

    assert result["scan_id"] == "scan-123"
    #key has fake in it so it should never hit the internet
    assert not mock_get.called
    assert result["status"] == "completed"

    assert "phishing_surface" in result["raw_result"]
    #if local mock file is loading it should have a pattern and emails
    assert "email_format_pattern" in result["raw_result"]["phishing_surface"]