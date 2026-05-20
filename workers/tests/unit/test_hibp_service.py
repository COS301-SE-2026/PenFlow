from unittest.mock import patch, MagicMock
from app.services.hibp_service import run_hibp

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
        {"Name": "Dropbox", "Title": "Dropbox"}
    ]
    mock_get.return_value = mock_response

    #execution
    result = run_hibp("acorns.com")

    #assertions
    assert result["status"] == "completed"
    assert mock_get.called #proves it hit the internet
    assert result["raw_result"]["provider"] == "HaveIBeenPwned"
    assert result["raw_result"]["pwned_accounts_count"] == 3
    assert "LinkedIn" in result["raw_result"]["known_breaches"]
    assert len(result["findings"]) == 1 #should generate a high-severity finding


#sad path for api outage
@patch("app.services.hibp_service.httpx.Client.get")
@patch("app.services.hibp_service.HIBP_API_KEY", "Real_Cos_301_FUN")
@patch("app.services.hibp_service.SCAN_MODE", "LIVE")
def test_hibp_live_api_failure(mock_get):
    """Test that an HTTP error gracefully degrades into a failed status."""
    
    import httpx
    #force a network crash
    mock_get.side_effect = httpx.HTTPError("HIBP API Down")
    
    #execution
    result = run_hibp("acorns.com")
    
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
    result = run_hibp("acorns.com")

    #key is fake so it should never attempt a network request
    assert not mock_get.called 
    assert result["status"] == "completed"
    
    #mock data should load safely
    assert "pwned_accounts_count" in result["raw_result"]