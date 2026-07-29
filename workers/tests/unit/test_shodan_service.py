from unittest.mock import MagicMock, patch

from app.tasks.shodan_tasks import run_shodan


#live happy path
@patch("app.tasks.shodan_tasks.send_source_callback")
@patch("app.services.shodan_service.socket.gethostbyname")
@patch("app.services.shodan_service.httpx.Client.get")
@patch("app.services.shodan_service.SHODAN_API_KEY", "COS_301_1s_FUN")
@patch("app.services.shodan_service.SCAN_MODE", "LIVE")
def test_shodan_live_happy_path(mock_get, mock_socket, mock_send_callback):
    """Test that a real key triggers IP resolution and a live Shodan API request."""
    
    #fake the ip resolution


    TEST_IP = "151.101.130.49"

    mock_socket.return_value = TEST_IP #NOSONAR

    #fake the live api response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "ip_str": TEST_IP,
        "org": "Fastly, Inc.",
        "ports": [80, 443],
    }
    mock_get.return_value = mock_response

    #execution
    result = run_shodan("scan-123", "acorns.com")

    #assertions
    assert result["status"] == "completed"
    assert result["scan_id"] == "scan-123"
    assert result["source_name"] == "shodan"
    assert mock_get.called #proves it hit the internet
    assert mock_socket.called #proves it resolved the IP
    assert result["raw_result"]["infrastructure"]["hosting_provider"] == "Fastly, Inc."
    assert len(result["raw_result"]["infrastructure"]["open_ports"]) == 2
    mock_send_callback.assert_called_once()


#sad path for api outage
@patch("app.tasks.shodan_tasks.send_source_callback")
@patch("app.services.shodan_service.socket.gethostbyname")
@patch("app.services.shodan_service.httpx.Client.get")
@patch("app.services.shodan_service.SHODAN_API_KEY", "COS_301_1s_FUN")
@patch("app.services.shodan_service.SCAN_MODE", "LIVE")
def test_shodan_live_api_failure(mock_get, mock_socket, mock_send_callback):
    """Test that a network crash gracefully degrades to a failed status."""
    
    import httpx
    mock_socket.return_value = "151.101.130.49" #NOSONAR
    
    #force a network crash
    mock_get.side_effect = httpx.HTTPError("Shodan API Down")
    
    #execution
    result = run_shodan("scan-123", "acorns.com")
    
    #expect clean failure dict
    assert result["status"] == "failed"
    assert result["scan_id"] == "scan-123"
    assert "error" in result["raw_result"]["infrastructure"]
    mock_send_callback.assert_called_once()


#mock fallback path
@patch("app.tasks.shodan_tasks.send_source_callback")
@patch("app.services.shodan_service.socket.gethostbyname")
@patch("app.services.shodan_service.httpx.Client.get")
@patch("app.services.shodan_service.SHODAN_API_KEY", "fake_key_1234")
@patch("app.services.shodan_service.SCAN_MODE", "LIVE")
def test_shodan_fallback_to_mock(mock_get, mock_socket, mock_send_callback):
    """Test that a fake key safely bypasses the internet and loads local mock data."""
    
    #execution
    result = run_shodan("scan-123", "acorns.com")

    #key is fake so it should never attempt a network request or DNS resolution
    assert not mock_get.called 
    assert not mock_socket.called
    assert result["status"] == "completed"
    assert result["scan_id"] == "scan-123"
    
    #mock data should load safely
    assert "hosting_provider" in result["raw_result"]["infrastructure"]
    mock_send_callback.assert_called_once()


@patch("app.tasks.shodan_tasks.send_source_callback")
@patch("app.tasks.shodan_tasks.collect_raw_data")
def test_hibp_exception(mock_raw_data, mock_send_callback):
    mock_raw_data.side_effect = Exception("Some shodan exception")

    result = run_shodan("scan-1234", "acorns.com")

    assert result == {
        "scan_id": "scan-1234",
        "source_name": "shodan",
        "status": "failed",
        "raw_result": {"error": "Some shodan exception"},
        "findings": [],
        "assets": [],
        "error_message": "Some shodan exception",
    }

    mock_send_callback.assert_called_once_with(
        scan_id = "scan-1234",
        source_name = "shodan",
        status = "failed",
        raw_result = {"error": "Some shodan exception"},
        findings = [],
        assets = [],
        error_message = "Some shodan exception",
    )