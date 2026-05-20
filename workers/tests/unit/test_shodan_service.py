from unittest.mock import patch, MagicMock
from app.services.shodan_service import run_shodan

#live happy path
@patch("app.services.shodan_service.socket.gethostbyname")
@patch("app.services.shodan_service.httpx.Client.get")
@patch("app.services.shodan_service.SHODAN_API_KEY", "COS_301_1s_FUN")
@patch("app.services.shodan_service.SCAN_MODE", "LIVE")
def test_shodan_live_happy_path(mock_get, mock_socket):
    """Test that a real key triggers IP resolution and a live Shodan API request."""
    
    #fake the ip resolution
    mock_socket.return_value = "151.101.130.49"

    #fake the live api response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "org": "Fastly, Inc.",
        "ports": [80, 443],
        "data": [
            {"port": 80, "transport": "tcp"},
            {"port": 443, "transport": "tcp"}
        ]
    }
    mock_get.return_value = mock_response

    #execution
    result = run_shodan("acorns.com")

    #assertions
    assert result["status"] == "completed"
    assert mock_get.called #proves it hit the internet
    assert mock_socket.called #proves it resolved the IP
    assert result["raw_result"]["infrastructure"]["hosting_provider"] == "Fastly, Inc."
    assert len(result["raw_result"]["infrastructure"]["open_ports"]) == 2


#sad path for api outage
@patch("app.services.shodan_service.socket.gethostbyname")
@patch("app.services.shodan_service.httpx.Client.get")
@patch("app.services.shodan_service.SHODAN_API_KEY", "COS_301_1s_FUN")
@patch("app.services.shodan_service.SCAN_MODE", "LIVE")
def test_shodan_live_api_failure(mock_get, mock_socket):
    """Test that a network crash gracefully degrades to a failed status."""
    
    import httpx
    mock_socket.return_value = "151.101.130.49"
    
    #force a network crash
    mock_get.side_effect = httpx.HTTPError("Shodan API Down")
    
    #execution
    result = run_shodan("acorns.com")
    
    #expect clean failure dict
    assert result["status"] == "failed"
    assert "error" in result["raw_result"]["infrastructure"]


#mock fallback path
@patch("app.services.shodan_service.socket.gethostbyname")
@patch("app.services.shodan_service.httpx.Client.get")
@patch("app.services.shodan_service.SHODAN_API_KEY", "fake_key_1234")
@patch("app.services.shodan_service.SCAN_MODE", "LIVE")
def test_shodan_fallback_to_mock(mock_get, mock_socket):
    """Test that a fake key safely bypasses the internet and loads local mock data."""
    
    #execution
    result = run_shodan("acorns.com")

    #key is fake so it should never attempt a network request or DNS resolution
    assert not mock_get.called 
    assert not mock_socket.called
    assert result["status"] == "completed"
    
    #mock data should load safely
    assert "hosting_provider" in result["raw_result"]["infrastructure"]