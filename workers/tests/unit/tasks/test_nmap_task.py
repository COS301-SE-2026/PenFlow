from unittest.mock import patch

from app.tasks.nmap_task import run_nmap_scan

TARGETS = [
    {
        "hostname": "test.com",
        "ipv4": ["1.1.1.1"],
        "ipv6": [],
    }
]


@patch("app.tasks.nmap_task.celery_app.send_task")
@patch("app.tasks.nmap_task.send_source_callback")
@patch(
    "app.tasks.nmap_task.get_technologies_from_db",
    return_value=[{"product": "nginx"}],
)
@patch(
    "app.tasks.nmap_task.dispatch_scan_job",
    return_value=True,
)
def test_combined_pipeline_success(
    mock_dispatch,
    mock_get_technologies,
    mock_send_callback,
    mock_send_task,
):
    result = run_nmap_scan.run(
        scan_id="scan1",
        targets=TARGETS,
    )

    assert result == {
        "status": "completed",
        "scan_id": "scan1",
        "source_name": "nmap",
        "unique_addresses": 1,
    }

    mock_dispatch.assert_called_once_with(
        "phase2_pipeline",
        {
            "scan_id": "scan1",
            "targets": TARGETS,
            "profile": "standard",
        },
    )
    mock_get_technologies.assert_called_once_with(
        "scan1"
    )
    mock_send_callback.assert_not_called()
    mock_send_task.assert_called_once_with(
        "scan.phase2_cpe_resolver",
        args=[
            "scan1",
            [{"product": "nginx"}],
        ],
    )


@patch("app.tasks.nmap_task.celery_app.send_task")
@patch("app.tasks.nmap_task.send_source_callback")
@patch("app.tasks.nmap_task.get_technologies_from_db")
@patch(
    "app.tasks.nmap_task.dispatch_scan_job",
    return_value=False,
)
def test_combined_pipeline_failure_finishes_sources(
    mock_dispatch,
    mock_get_technologies,
    mock_send_callback,
    mock_send_task,
):
    result = run_nmap_scan.run(
        scan_id="scan1",
        targets=TARGETS,
    )

    assert result == {
        "status": "failed",
        "scan_id": "scan1",
        "source_name": "nmap",
        "unique_addresses": 1,
    }

    mock_dispatch.assert_called_once()
    mock_get_technologies.assert_not_called()
    mock_send_task.assert_not_called()

    assert [
        callback.kwargs["source_name"]
        for callback in mock_send_callback.call_args_list
    ] == [
        "nmap",
        "http_security",
        "tls",
        "fingerprint",
        "cve",
    ]

    assert all(
        callback.kwargs["status"] == "failed"
        for callback in mock_send_callback.call_args_list[
            :4
        ]
    )
    assert (
        mock_send_callback.call_args_list[-1].kwargs[
            "status"
        ]
        == "skipped"
    )