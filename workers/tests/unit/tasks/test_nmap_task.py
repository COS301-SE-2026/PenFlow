from unittest.mock import patch

from app.tasks.nmap_task import run_nmap_scan


#Happy Path 1
#Successful scan with callback
@patch("app.tasks.nmap_task.celery_app.send_task")
@patch("app.tasks.nmap_task.send_source_callback")
@patch("app.tasks.nmap_task.run_live_nmap_scan")
def test_successful_task(mock_scan, mock_callback, mock_send_task):

    mock_scan.return_value = \
    {
        "ip": "1.1.1.1",
        "status": "up",
        "hostnames": [],
        "ports":
        [
            {
                "port": 22,
                "protocol": "tcp",
                "service": "ssh",
                "product": "CoolSSH",
                "version": "9.0",
                "state": "open",
            }
        ],
    }

    result = run_nmap_scan.run\
    (
        scan_id="scan1",
        ip_address="1.1.1.1",
        domain="test.com",
    )

    assert result["status"] == "completed"
    assert len(result["services"]) == 1
    service = result["services"][0]
    assert service["host"] == "1.1.1.1"
    assert service["port"] == 22
    assert service["protocol"] == "tcp"
    assert service["service_name"] == "ssh"
    mock_callback.assert_called_once()
    assert mock_send_task.call_count == 3

#Sad Path 1
#Service failure also with callback
@patch("app.tasks.nmap_task.send_source_callback")
@patch("app.tasks.nmap_task.run_live_nmap_scan")
def test_failed_task(mock_scan, mock_callback):

    mock_scan.side_effect = Exception("Boom")

    result = run_nmap_scan.run\
    (
        scan_id="scan1",
        ip_address="1.1.1.1",
        domain="test.com",
    )

    assert result["status"] == "failed"
    assert result["services"] == []
    assert "error_message" in result

    mock_callback.assert_called_once()