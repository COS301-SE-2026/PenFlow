from unittest.mock import patch, MagicMock
from app.services.wappalyzer_service import run_wappalyzer

#live happy path
@patch("app.services.wappalyzer_service.WebPage.new_from_url")
@patch("app.services.wappalyzer_service.Wappalyzer.latest")
@patch("app.services.wappalyzer_service.SCAN_MODE", "LIVE")
def test_wappalyzer_live_happy_path(mock_wappalyzer_latest, mock_webpage):
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
    result = run_wappalyzer("acorns.com")

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


#sad path for engine outage
@patch("app.services.wappalyzer_service.WebPage.new_from_url")
@patch("app.services.wappalyzer_service.Wappalyzer.latest")
@patch("app.services.wappalyzer_service.SCAN_MODE", "LIVE")
def test_wappalyzer_live_engine_failure(_mock_wappalyzer_latest, mock_webpage):
    """Test that a local engine crash gracefully degrades into a failed status."""
    
    #force a crash when trying to fetch the webpage
    mock_webpage.side_effect = Exception("Connection Timeout")
    
    #execution
    result = run_wappalyzer("acorns.com")
    
    #expect clean failure dict
    assert result["status"] == "failed"
    assert "error" in result["raw_result"]["tech_stack"]


#mock fallback path
@patch("app.services.wappalyzer_service.WebPage.new_from_url")
@patch("app.services.wappalyzer_service.Wappalyzer.latest")
@patch("app.services.wappalyzer_service.SCAN_MODE", "MOCK")
def test_wappalyzer_fallback_to_mock(mock_wappalyzer_latest, mock_webpage):
    """Test that the worker safely bypasses the local engine and loads local mock data."""
    
    #execution
    result = run_wappalyzer("acorns.com")
    assert not mock_wappalyzer_latest.called
    assert not mock_webpage.called
    assert result["status"] == "completed"