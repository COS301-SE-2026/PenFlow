from unittest.mock import MagicMock, patch

import httpx

from app.tasks.urlscan_tasks import run_urlscan


#Test happy path for our url loop
@patch("app.tasks.urlscan_tasks.send_source_callback")
@patch("app.services.urlscan_service._download_screenshot")
@patch("app.services.urlscan_service.httpx.Client.get")
@patch("app.services.urlscan_service.httpx.Client.post")
@patch("app.services.urlscan_service.URLSCAN_API_KEY", "live_key_999")
@patch("app.services.urlscan_service.SCAN_MODE", "LIVE")
def test_urlscan_live_happy_path(mock_post, mock_get, mock_download, mock_send_callback):
    """Test the two-step POST/GET polling loop works correctly without file I/O."""
    #scan queued
    mock_post_res = MagicMock()
    mock_post_res.json.return_value = {"uuid": "test-uuid-1234"}
    mock_post.return_value = mock_post_res
    #data recieved
    mock_get_res = MagicMock()
    mock_get_res.status_code = 200
    mock_get_res.json.return_value = {
        "verdicts": {"overall": {"malicious": False}},
        "task": {"uuid": "test-uuid-1234"},
    }
    mock_get.return_value = mock_get_res
    #mock the screenshot download
    mock_download.return_value = "/app/generated_reports/screenshots/test_screenshot.png"
    #Execute
    result = run_urlscan("scan-123", "acorns.com")
    #testing the response is exactly how we want it
    assert result["scan_id"] == "scan-123"
    assert result["status"] == "completed"
    assert result["source_name"] == "urlscan"
    assert result["raw_result"]["reputation"]["malicious_flags"] == 0
    assert result["raw_result"]["reputation"]["urlscan_uuid"] == "test-uuid-1234"
    mock_send_callback.assert_called_once()


#Test sad path now connection
@patch("app.tasks.urlscan_tasks.send_source_callback")
@patch("app.services.urlscan_service.httpx.Client.post")
@patch("app.services.urlscan_service.URLSCAN_API_KEY", "live_key_999")
@patch("app.services.urlscan_service.SCAN_MODE", "LIVE")
def test_urlscan_live_api_failure(mock_post, mock_send_callback):
    #force an erro
    mock_post.side_effect = httpx.HTTPError("API Down")

    result = run_urlscan("scan-123", "acorns.com")
    #expected output to protect db and pdf builder
    assert result["scan_id"] == "scan-123"
    assert result["status"] == "failed"
    assert "error" in result["raw_result"]["reputation"]
    mock_send_callback.assert_called_once()


#Test mock mode to see if it loads
@patch("app.tasks.urlscan_tasks.send_source_callback")
@patch("app.services.urlscan_service.httpx.Client.post")
@patch("app.services.urlscan_service.httpx.Client.get")
@patch("app.services.urlscan_service.SCAN_MODE", "MOCK")
def test_urlscan_mock_mode_fallback(mock_get, mock_post, mock_send_callback):
    """Test that the worker safely bypasses the internet and loads local data in MOCK mode."""
    result = run_urlscan("scan-123", "acorns.com")
    assert result["scan_id"] == "scan-123"
    assert not mock_post.called
    assert not mock_get.called
    assert result["status"] == "completed"
    assert result["source_name"] == "urlscan"
    # Verify the Normalizer successfully flattened the mock JSON
    reputation = result["raw_result"]["reputation"]
    assert "malicious_flags" in reputation
    assert reputation["provider"] == "URLScan"
    mock_send_callback.assert_called_once()