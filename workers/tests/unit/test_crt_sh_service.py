from unittest.mock import MagicMock, patch

from app.tasks.crtsh_tasks import run_crt_sh


# Test for "happy paths"
@patch("app.tasks.crtsh_tasks.send_source_callback")
@patch("app.services.crt_sh_service.SCAN_MODE", "LIVE")
@patch("app.services.crt_sh_service.httpx.Client.get")
def test_crt_sh_live_happy_path(mock_get, mock_send_callback):
    """Test that the worker successfully extracts and deduplicates live subdomains."""
    
    # Fake successful HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "Valid JSON string here"
    mock_response.json.return_value = [
        {"name_value": "acorns.com"},
        {"name_value": "api.acorns.com\n*.acorns.com"}, 
        {"name_value": "app.acorns.com"}
    ]
    mock_get.return_value = mock_response

    result = run_crt_sh("scan-123", "acorns.com")

    # should be exact responses
    assert result["status"] == "completed"
    assert result["source_name"] == "crt.sh"
    assert result["raw_result"]["subdomains"]["total_found"] == 3
    assert result["raw_result"]["subdomains"]["discovered_names"] == [
        "acorns.com",
        "api.acorns.com",
        "app.acorns.com",
    ]
    mock_send_callback.assert_called_once()


# Test sad paths for api issues
@patch("app.tasks.crtsh_tasks.send_source_callback")
@patch("app.services.crt_sh_service.SCAN_MODE", "LIVE")
@patch("app.services.crt_sh_service.time.sleep") 
@patch("app.services.crt_sh_service.httpx.Client.get")
def test_crt_sh_sad_path_502_loop(mock_get, mock_sleep, mock_send_callback):
    """Test that the worker exhausts its retries on 502 Bad Gateway without crashing."""
    
    # Fake a perpetually failing HTTP server
    mock_response = MagicMock()
    mock_response.status_code = 502
    mock_get.return_value = mock_response

    result = run_crt_sh("scan-123", "acorns.com")

    #we cant return errors beacuse the pdf builder expects specific data, 
    # test to see how we handle errors and if we fail gracefully with the expected output.
    assert result["status"] == "failed"
    assert result["raw_result"]["subdomains"]["total_found"] == 0
    assert result["raw_result"]["subdomains"]["discovered_names"] == []
    
    # Prove our "Fail Fast" retry loops fired exactly 6 times
    assert mock_get.call_count == 3
    assert mock_sleep.call_count == 2
    mock_send_callback.assert_called_once()


#test mock mode to see if it loads
@patch("app.tasks.crtsh_tasks.send_source_callback")
@patch("app.services.crt_sh_service.SCAN_MODE", "MOCK")
@patch("app.services.crt_sh_service.httpx.Client.get")
def test_crt_sh_mock_mode_fallback(mock_get, mock_send_callback):
    """Test that the worker safely bypasses the internet and loads local data in MOCK mode."""
    
    result = run_crt_sh("scan-123", "acorns.com")
    
    #mock shouldnt run httpx or any requests.
    assert not mock_get.called
    assert result["status"] == "completed"
    assert result["raw_result"]["subdomains"]["total_found"] > 0
    mock_send_callback.assert_called_once()


@patch("app.tasks.crtsh_tasks.send_source_callback")
@patch("app.tasks.crtsh_tasks.collect_raw_data")
def test_crtsh_exception(mock_raw_data, mock_send_callback):
    mock_raw_data.side_effect = Exception("Some crt.sh exception")

    result = run_crt_sh("scan-1234", "acorns.com")

    assert result == {
        "scan_id": "scan-1234",
        "source_name": "crt.sh",
        "status": "failed",
        "raw_result": {"error": "Some crt.sh exception"},
        "findings": [],
        "assets": [],
        "services": [],
        "technologies": [],
        "error_message": "Some crt.sh exception",
    }

    mock_send_callback.assert_called_once_with(
        scan_id = "scan-1234",
        source_name = "crt.sh",
        status = "failed",
        raw_result = {"error": "Some crt.sh exception"},
        findings = [],
        assets = [],
        services = [],
        technologies = [],
        error_message = "Some crt.sh exception",
    )