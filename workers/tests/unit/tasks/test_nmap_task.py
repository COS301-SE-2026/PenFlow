from unittest.mock import patch

from app.tasks.nmap_task import run_nmap_scan


@patch("app.tasks.nmap_task.celery_app.send_task")
@patch("app.tasks.nmap_task.send_source_callback")
@patch("app.tasks.nmap_task.get_technologies_from_db", return_value=[])
@patch("app.tasks.nmap_task.get_ports_from_db", return_value=[])
@patch("app.tasks.nmap_task.dispatch_scan_job", return_value=True)
def test_successful_dispatcher_chaining(
    mock_dispatch,
    mock_get_ports,
    mock_get_technologies,
    mock_send_callback,
    mock_send_task,
):

    targets = [
        {
            "hostname": "test.com",
            "ipv4": ["1.1.1.1"],
            "ipv6": [],
        }
    ]

    result = run_nmap_scan.run(
        scan_id="scan1",
        targets=targets,
    )

    assert result == {
        "status": "completed",
        "scan_id": "scan1",
        "source_name": "nmap",
        "unique_addresses": 1,
    }

    mock_dispatch.assert_called_once_with(
        "nmap",
        {
            "scan_id": "scan1",
            "ip_address": "1.1.1.1",
            "profile": "standard",
            "defer_source_completion": True,
        },
    )

    mock_get_ports.assert_called_once_with(
        "scan1",
        "1.1.1.1",
    )
    mock_get_technologies.assert_called_once_with("scan1")
    assert mock_send_callback.call_count > 0

    mock_send_task.assert_called_once_with(
        "scan.phase2_cpe_resolver",
        args=["scan1", []],
    )