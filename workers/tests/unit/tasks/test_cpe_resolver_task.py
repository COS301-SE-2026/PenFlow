from unittest.mock import patch

from app.tasks.cpe_resolver_task import run_cpe_resolver_task


@patch("app.tasks.cpe_resolver_task.celery_app.send_task")
@patch("app.tasks.cpe_resolver_task.send_source_callback")
@patch("app.tasks.cpe_resolver_task.run_cpe_resolution")
def test_run_cpe_resolver_task_success(mock_run, mock_callback, mock_send_task):
    resolved_inventory = \
    [
        {
            "vendor": "apache",
            "product": "tomcat",
            "cpe": "cpe:2.3:a:apache:tomcat:10.1.0:*:*:*:*:*:*:*",
        }
    ]

    mock_run.return_value = resolved_inventory

    result = run_cpe_resolver_task.run\
    (
        scan_id="scan-123",
        software_inventory=[],
    )

    assert result["status"] == "completed"
    assert result["source_name"] == "cpe_resolver"
    assert len(result["assets"]) == 1

    asset = result["assets"][0]

    assert asset["type"] == "resolved_software"
    assert asset["value"] == resolved_inventory[0]["cpe"]

    mock_callback.assert_called_once()
    mock_send_task.assert_called_once_with(
        "scan.phase2_cve",
        args=["scan-123", resolved_inventory],
    )


@patch("app.tasks.cpe_resolver_task.celery_app.send_task")
@patch("app.tasks.cpe_resolver_task.send_source_callback")
@patch("app.tasks.cpe_resolver_task.run_cpe_resolution")
def test_run_cpe_resolver_task_empty(mock_run, mock_callback, mock_send_task):
    mock_run.return_value = []

    result = run_cpe_resolver_task.run\
    (
        scan_id="scan-123",
        software_inventory=[],
    )

    assert result["status"] == "completed"
    assert result["assets"] == []

    mock_callback.assert_called_once()
    mock_send_task.assert_called_once_with(
        "scan.phase2_cve",
        args=["scan-123", []],
    )


@patch("app.tasks.cpe_resolver_task.send_source_callback")
@patch("app.tasks.cpe_resolver_task.run_cpe_resolution")
def test_run_cpe_resolver_task_failure(mock_run, mock_callback):
    mock_run.side_effect = Exception("Resolver failed")

    result = run_cpe_resolver_task.run\
    (
        scan_id="scan-456",
        software_inventory=[],
    )

    assert result["status"] == "failed"
    assert result["assets"] == []
    assert result["error_message"] == "Resolver failed"

    mock_callback.assert_called_once()