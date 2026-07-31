from unittest.mock import MagicMock, patch

from app.tasks.wappalyzer_tasks import run_wappalyzer


#live happy path
@patch("app.tasks.wappalyzer_tasks.send_source_callback")
@patch("app.services.wappalyzer_service.WebPage.new_from_url")
@patch("app.services.wappalyzer_service.Wappalyzer.latest")
@patch("app.services.wappalyzer_service.SCAN_MODE", "LIVE")
def test_wappalyzer_live_happy_path(mock_wappalyzer_latest, mock_webpage, mock_send_callback):
    """Test that the native Wappalyzer library executes and parses correctly."""
    
    #fake the page object
    mock_page_instance = MagicMock()
    mock_webpage.return_value = mock_page_instance
    mock_engine_instance = MagicMock()
    mock_engine_instance.analyze_with_versions_and_categories.return_value = \
    {
        "WordPress": {"versions": ["5.8"], "categories": ["CMS"]},
        "PHP": {"versions": ["8.1"], "categories": ["Programming languages"]},
        "React": {"versions": [], "categories": ["JavaScript frameworks"]}
    }
    mock_wappalyzer_latest.return_value = mock_engine_instance

    #execution
    result = run_wappalyzer("scan-123", "acorns.com")

    #assertions
    assert result["status"] == "completed"
    assert mock_webpage.called
    assert mock_wappalyzer_latest.called
    
    tech_stack = result["raw_result"]["tech_stack"]
    assert len(tech_stack["cms"]) == 1
    assert tech_stack["cms"][0]["name"] == "WordPress"
    assert tech_stack["programmingLanguages"][0]["name"] == "PHP"
    assert tech_stack["frameworks"][0]["name"] == "React"
    assert len(result["findings"]) == 2
    mock_send_callback.assert_called_once()


#sad path for engine outage
@patch("app.tasks.wappalyzer_tasks.send_source_callback")
@patch("app.services.wappalyzer_service.WebPage.new_from_url")
@patch("app.services.wappalyzer_service.Wappalyzer.latest")
@patch("app.services.wappalyzer_service.SCAN_MODE", "LIVE")
def test_wappalyzer_live_engine_failure(_mock_wappalyzer_latest, mock_webpage, mock_send_callback):
    """Test that a local engine crash gracefully degrades into a failed status."""
    
    #force a crash when trying to fetch the webpage
    mock_webpage.side_effect = Exception("Connection Timeout")
    
    #execution
    result = run_wappalyzer("scan-123", "acorns.com")
    
    #expect clean failure dict
    assert result["status"] == "failed"
    assert "error" in result["raw_result"]["tech_stack"]
    mock_send_callback.assert_called_once()


#mock fallback path
@patch("app.tasks.wappalyzer_tasks.send_source_callback")
@patch("app.services.wappalyzer_service.WebPage.new_from_url")
@patch("app.services.wappalyzer_service.Wappalyzer.latest")
@patch("app.services.wappalyzer_service.SCAN_MODE", "MOCK")
def test_wappalyzer_fallback_to_mock(mock_wappalyzer_latest, mock_webpage, mock_send_callback):
    """Test that the worker safely bypasses the local engine and loads local mock data."""
    
    #execution
    result = run_wappalyzer("scan-123", "acorns.com")
    assert not mock_wappalyzer_latest.called
    assert not mock_webpage.called
    assert result["status"] == "completed"
    mock_send_callback.assert_called_once()


@patch("app.tasks.wappalyzer_tasks.send_source_callback")
@patch("app.tasks.wappalyzer_tasks.collect_raw_data")
def test_hibp_exception(mock_raw_data, mock_send_callback):
    mock_raw_data.side_effect = Exception("Some wappalyzer exception")

    result = run_wappalyzer("scan-1234", "acorns.com")

    assert result == {
        "scan_id": "scan-1234",
        "source_name": "wappalyzer",
        "status": "failed",
        "raw_result": {"error": "Some wappalyzer exception"},
        "findings": [],
        "assets": [],
        "services": [],
        "technologies": [],
        "error_message": "Some wappalyzer exception",
    }

    mock_send_callback.assert_called_once_with(
        scan_id = "scan-1234",
        source_name = "wappalyzer",
        status = "failed",
        raw_result = {"error": "Some wappalyzer exception"},
        findings = [],
        assets = [],
        services = [],
        technologies = [],
        error_message = "Some wappalyzer exception",
    )