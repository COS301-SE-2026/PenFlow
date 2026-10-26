from unittest.mock import MagicMock, patch

import httpx

from app.tasks.urlscan_tasks import run_urlscan

SCAN_ID = "00000000-0000-4000-8000-000000000001"
# Test happy path for our url loop
@patch("app.tasks.urlscan_tasks.send_source_callback")
@patch("app.services.urlscan_service._download_screenshot")
@patch("app.services.urlscan_service.httpx.Client.get")
@patch("app.services.urlscan_service.httpx.Client.post")
@patch("app.services.urlscan_service.URLSCAN_API_KEY", "live_key_999")
@patch("app.services.urlscan_service.SCAN_MODE", "LIVE")
def test_urlscan_live_happy_path(
    mock_post, 
    mock_get, 
    mock_download, 
    mock_send_callback,
    monkeypatch,
):
    
    """Test the two-step POST/GET polling loop works correctly without file I/O."""
    monkeypatch.setattr(
        "app.services.urlscan_service.resolve_public_host",
        lambda *args, **kwargs: ["1.1.1.1"],
    )
    # scan queued
    mock_post_res = MagicMock()
    mock_post_res.json.return_value = {"uuid": "550e8400-e29b-41d4-a716-446655440000"}
    mock_post.return_value = mock_post_res
    # data recieved
    mock_get_res = MagicMock()
    mock_get_res.status_code = 200
    mock_get_res.json.return_value = {
        "verdicts": {"overall": {"malicious": False}},
        "task": {"uuid": "550e8400-e29b-41d4-a716-446655440000"},
    }
    mock_get.return_value = mock_get_res
    # mock the screenshot download
    mock_download.return_value = "scan-screenshot.png"
    # Execute
    result = run_urlscan(SCAN_ID, "acorns.com")
    # testing the response is exactly how we want it
    assert result["scan_id"] == SCAN_ID
    assert result["status"] == "completed"
    assert result["source_name"] == "urlscan"
    assert result["raw_result"]["reputation"]["malicious_flags"] == 0
    assert (
        result["raw_result"]["reputation"]["urlscan_uuid"] 
        == "550e8400-e29b-41d4-a716-446655440000"
    )
    assert mock_send_callback.call_count == 2


# Test sad path now connection
@patch("app.tasks.urlscan_tasks.send_source_callback")
@patch("app.services.urlscan_service.httpx.Client.post")
@patch("app.services.urlscan_service.URLSCAN_API_KEY", "live_key_999")
@patch("app.services.urlscan_service.SCAN_MODE", "LIVE")
def test_urlscan_live_api_failure(mock_post, mock_send_callback, monkeypatch):
    monkeypatch.setattr(
        "app.services.urlscan_service.resolve_public_host",
        lambda *args, **kwargs: ["1.1.1.1"],
    )
    # force an erro
    mock_post.side_effect = httpx.HTTPError("API Down")

    result = run_urlscan(SCAN_ID, "acorns.com")
    # expected output to protect db and pdf builder
    assert result["scan_id"] == SCAN_ID
    assert result["status"] == "failed"
    assert "error" in result["raw_result"]["reputation"]
    assert mock_send_callback.call_count == 2


# Test mock mode to see if it loads
@patch("app.tasks.urlscan_tasks.send_source_callback")
@patch("app.services.urlscan_service.httpx.Client.post")
@patch("app.services.urlscan_service.httpx.Client.get")
@patch("app.services.urlscan_service.SCAN_MODE", "MOCK")
def test_urlscan_mock_mode_fallback(mock_get, mock_post, mock_send_callback):
    """Test that the worker safely bypasses the internet and loads local data in MOCK mode."""
    result = run_urlscan(SCAN_ID, "acorns.com")
    assert result["scan_id"] == SCAN_ID
    assert not mock_post.called
    assert not mock_get.called
    assert result["status"] == "completed"
    assert result["source_name"] == "urlscan"
    # Verify the Normalizer successfully flattened the mock JSON
    reputation = result["raw_result"]["reputation"]
    assert "malicious_flags" in reputation
    assert reputation["provider"] == "URLScan"
    assert mock_send_callback.call_count == 2


@patch("app.tasks.urlscan_tasks.send_source_callback")
@patch("app.tasks.urlscan_tasks.collect_raw_data")
def test_hibp_exception(mock_raw_data, mock_send_callback):
    mock_raw_data.side_effect = Exception("Some urlscan exception")

    result = run_urlscan(SCAN_ID, "acorns.com")

    assert result == {
        "scan_id": SCAN_ID,
        "source_name": "urlscan",
        "status": "failed",
        "raw_result": {"error": "Some urlscan exception"},
        "findings": [],
        "assets": [],
        "services": [],
        "technologies": [],
        "error_message": "Some urlscan exception",
    }

    assert mock_send_callback.call_count == 2
    mock_send_callback.assert_any_call(
        scan_id=SCAN_ID,
        source_name="urlscan",
        status="failed",
        raw_result={"error": "Some urlscan exception"},
        findings=[],
        assets=[],
        services=[],
        technologies=[],
        error_message="Some urlscan exception",
    )
