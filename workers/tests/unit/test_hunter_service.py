from unittest.mock import patch, MagicMock
from app.services.hunter_service import run_hunter

#live happy path
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
                {"value": "info@acorns.com", "type": "generic", "confidence": 80}
            ]
        }
    }
    mock_get.return_value = mock_response

    #execution
    result = run_hunter("acorns.com")

    #assertions
    assert result["status"] == "completed"
    assert mock_get.called #proves it hit the live internet block
    assert result["raw_result"]["provider"] == "Hunter.io"
    assert len(result["raw_result"]["public_emails_found"]) == 2
    assert len(result["findings"]) == 1 #should generate 1 finding for discovered emails


#sad path for api outage
@patch("app.services.hunter_service.httpx.Client.get")
@patch("app.services.hunter_service.HUNTER_API_KEY", "a_real_key_301")
@patch("app.services.hunter_service.SCAN_MODE", "LIVE")
def test_hunter_live_api_failure(mock_get):
    """Test that an HTTP error gracefully degrades into a failed status."""
    
    import httpx
    #force a network crash
    mock_get.side_effect = httpx.HTTPError("Hunter API Down")
    
    #execution
    result = run_hunter("acorns.com")
    
    #expect a clean failure dict not a crash
    assert result["status"] == "failed"
    assert "error" in result["raw_result"]


#mock fallback path
@patch("app.services.hunter_service.httpx.Client.get")
@patch("app.services.hunter_service.HUNTER_API_KEY", "fake_key_1234")
@patch("app.services.hunter_service.SCAN_MODE", "LIVE") #force live mode to test fake key trigger
def test_hunter_fallback_to_mock(mock_get):
    """Test that a fake key gracefully degrades to the local mock file, even in LIVE mode."""
    
    #execution
    result = run_hunter("acorns.com")

    #key has fake in it so it should never hit the internet
    assert not mock_get.called 
    assert result["status"] == "completed"
    
    #if local mock file is loading it should have a pattern and emails
    assert "email_format_pattern" in result["raw_result"]