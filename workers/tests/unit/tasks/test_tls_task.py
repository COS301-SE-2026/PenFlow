import pytest

from unittest.mock import patch

from app.tasks.tls_task import run_tls_scan_task


##Happy Paths [Successful Scan]
@patch("app.tasks.tls_task.dispatch_scan_job")
@patch("app.tasks.tls_task.get_ports_from_db")
def test_successful_tls_scan\
(
    mock_get_ports,
    mock_dispatch
):
    """
    Successfully processes a TLS scan.
    """

    mock_get_ports.return_value = [{"port": 443, "protocol": "tcp", "service": "https"}]
    mock_dispatch.return_value = True 

    result = run_tls_scan_task.run(
        scan_id="scan123",
        ip_address="1.1.1.1",
        domain="hackerone.com",
        ports=[]
    )

    assert result["status"] == "completed"
    assert result["scan_id"] == "scan123"
    mock_dispatch.assert_called_once()

@patch("app.tasks.tls_task.send_source_callback")
@patch("app.tasks.tls_task.get_ports_from_db")
def test_skipped_tls_scan(mock_get_ports, mock_callback): 
    mock_get_ports.return_value = [] 

    result = run_tls_scan_task.run(
        scan_id="scan123", 
        ip_address="1.1.1.1",
        domain="hackerone.com",
        ports=[]
    )

    assert result["status"] == "skipped"
    mock_callback.assert_called_once_with(scan_id="scan123", source_name="tls", status="skipped")

@patch("app.tasks.tls_task.dispatch_scan_job")
@patch("app.tasks.tls_task.get_ports_from_db")
def test_failed_tls_scan(mock_get_ports, mock_dispatch):
    mock_get_ports.return_value = [{"port": 443, "protocol": "tcp", "service": "https"}]
    mock_dispatch.return_value = False 

    with pytest.raises(RuntimeError, match="Fargate/Docker container failed for TLS scan scan123"):
        run_tls_scan_task.run(
            scan_id="scan123",
            ip_address="1.1.1.1",
            domain="hackerone.com",
            ports=[]
        )