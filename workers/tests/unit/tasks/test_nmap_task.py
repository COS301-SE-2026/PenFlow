import pytest

from unittest.mock import patch

from app.tasks.nmap_task import run_nmap_scan

@patch("app.tasks.nmap_task.celery_app.send_task")
@patch("app.tasks.nmap_task.dispatch_scan_job")
def test_successful_dispatcher_chaining(mock_dispatch, mock_send_task):
    mock_dispatch.return_value = True

    result = run_nmap_scan.run(scan_id="scan1", ip_address="1.1.1.1", domain="test.com")

    assert result["status"] == "completed"
    assert mock_dispatch.call_count == 1 

    assert mock_send_task.call_count == 3 
    mock_send_task.assert_any_call("scan.phase2_tls", args=["scan1", "1.1.1.1", "test.com"])
    mock_send_task.assert_any_call("scan.phase2_http_security", args=["scan1", "test.com", "1.1.1.1"])
    mock_send_task.assert_any_call("scan.phase2_fingerprint", args=["scan1", "https://test.com", {}, None])

@patch("app.tasks.nmap_task.celery_app.send_task")
@patch("app.tasks.nmap_task.dispatch_scan_job")
def test_failed_dispatcher_aborts_chain(mock_dispatch, mock_send_task):
    mock_dispatch.return_value = False

    with pytest.raises(RuntimeError):
        run_nmap_scan.run(scan_id="scan1", ip_address="1.1.1.1", domain="test.com")

    assert mock_dispatch.call_count == 1
    assert mock_send_task.call_count == 0