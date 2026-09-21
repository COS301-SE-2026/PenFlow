import pytest 

from unittest.mock import MagicMock, patch

from app.tasks.fingerprinting_task import run_fingerprinting_scan_task


@patch("app.tasks.fingerprinting_task.celery_app.send_task")
@patch("app.task.fingerprinting_task.get_technologies_from_db")
@patch("app.tasks.fingerprinting_task.dispatch_scan_job")
@patch("app.tasks.fingerprinting_task.get_ports_from_db")
def test_run_fingerprinting_scan_task_success(mock_get_ports, mock_dispatch, mock_get_teach, mock_send_task):
    mock_get_ports.return_value = [{"port": 443, "protocol": "tcp", "service": "https"}]
    mock_dispatch.return_value = True 

    mock_get_tech.return_value = [{"product": "nginx", "version": "1.18.0", "category": "web_server"}]

    result = run_fingerprinting_scan_task.run(
        scan_id="scan-123",
        target_url="https://hackerone.com",
        nmap_data={},
        tls_data={}
    )

    assert result["status"] == "completed"
    assert result["scan_id"] == "scan-123"

    mock_dispatch.assert_called_once()

    mock_send_task.assert_called_once_with("scan.phase2_cpe_resolver", args=["scan-123", mock_get_tech.return_value])

@patch("app.tasks.fingerprinting_task.celery_app.send_task")
@patch("app.task.fingerprinting_task.dispatch_scan_job")
@patch("app.task.fingerprinting_task.get_ports_from_db")
def test_run_fingerprinting_scan_task_failure(mock_get_ports, mock_dispatch, mock_send_task):
    mock_get_ports.return_value = [{"port": 443, "protocol": "tcp", "service": "https"}]
    mock_dispatch.return_value = False 

    with pytest.raises(RuntimeError, match="Fargate/Docker container failed for Fingerprint scan scan-456"):
        run_fingerprinting_scan_task.run(
            scan_id="scan-456",
            target_url="https://hackerone.com",
            nmap_data={},
            tls_data={}
        )

    assert mock_send_task.call_count == 0