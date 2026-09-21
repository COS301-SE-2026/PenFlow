import pytest

from unittest.mock import patch

from app.tasks.http_security_task import run_http_security_scan_task

@patch("app.tasks.http_security_task.dispatch_scan_job")
@patch("app.tasks.http_security_task.get_ports_from_db")
def test_successful_scan(mock_get_ports, mock_dispatch):
    mock_get_ports.return_value = [{"port": 80, "protocol": "tcp", "service": "http"}]
    mock_dispatch.return_value = True 

    result = run_http_security_scan_task.run(
        scan_id="scan123",
        domain="hackerone.com",
        ip_address="1.1.1.1", 
        ports=[]
    )

    assert result["status"] == "completed"
    assert result["scan_id"] == "scan123"
    mock_dispatch.assert_called_once()

@patch("app.tasks.http_security_task.send_source_callback")
@patch("app.tasks.http_security_task.get_ports_from_db")
def test_skipped_http_scan(mock_get_ports, mock_callback):
    mock_get_ports.return_value = []

    result = run_http_security_scan_task.run(
        scan_id="scan123",
        domain="hackerone.com",
        ip_address="1.1.1.1",
        ports=[]
    )

    assert result["status"] == "skipped"
    mock_callback.assert_called_once_with(scan_id="scan123", source_name="http_security", status="skipped")

@patch("app.tasks.http_security_task.dispatch_scan_job")
@patch("app.tasks.http_security_task.get_ports_from_db")
def test_failed_http_scan(mock_get_ports, mock_dispatch):
    mock_get_ports.return_value = [{"port": 80, "protocol": "tcp", "service": "http"}]
    mock_dispatch.return_value = False 

    with pytest.raises(RuntimeError, match="Fargate/Docker container failed for HTTP Security scan scan123"):
        run_http_security_scan_task(
           scan_id="scan123",
           domain="hackerone.com",
           ip_address="1.1.1.1",
           ports=[] 
        )

        assert result["status"] == "skipped"
        mock_callback.assert_called_once_with(scan_id="scan123", source_name="http_security", status="skipped")

@patch("app.tasks.http_security_task.dispatch_scan_job")
@patch("app.tasks.http_security_task.get_ports_from_db")
def test_failed_http_scan(mock_get_ports, mock_dispatch):
    mock_get_ports.return_value = [{"port": 80, "protocol": "tcp", "service": "http"}]
    mock_dispatch.return_value = False 

    with pytest.raises(RuntimeError, match="Fargate/Docker container failed for HTTP Security scan scan123"):
        run_http_security_scan(
            scan_id="scan123",
            domain="hackerone.com",
            ip_address="1.1.1.1",
            ports=[]
        )