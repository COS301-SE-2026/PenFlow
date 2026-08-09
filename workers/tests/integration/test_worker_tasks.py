from unittest.mock import patch

from app.queue.celery_app import health_check
from app.tasks.wappalyzer_tasks import run_wappalyzer


@patch("app.tasks.wappalyzer_tasks.send_source_callback")
def test_wappalyzer_task_mock_mode(mock_callback):
    result = run_wappalyzer.delay(
        "test-scan-id",
        "hackerone.com",
    ).get()

    assert result["scan_id"] == "test-scan-id"
    assert result["source_name"] == "wappalyzer"
    assert "raw_result" in result
    assert "findings" in result
    assert mock_callback.call_count == 2

def test_worker_health_check():
    result = health_check.delay().get()

    assert result == "Worker is alive"