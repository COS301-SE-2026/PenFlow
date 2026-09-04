from unittest.mock import MagicMock, patch

from app.tasks.fingerprinting_task import run_fingerprinting_scan_task


@patch("app.tasks.fingerprinting_task.celery_app.send_task")
@patch("app.tasks.fingerprinting_task.send_source_callback")
@patch("app.tasks.fingerprinting_task.FingerprintingService")
def test_run_fingerprinting_scan_task_success(mock_service_class, mock_callback, mock_send_task):
    mock_service_instance = MagicMock()
    mock_service_class.return_value = mock_service_instance

    #The task only maps products and passes the metadata down.
    fake_fingerprint_results = \
        {
            "fingerprint":
                {
                    "software":
                        [
                            {
                                "product": "nginx",
                                "vendor": "f5",
                            }
                        ]
                }
        }

    mock_service_instance.run.return_value = fake_fingerprint_results

    result = run_fingerprinting_scan_task.run \
            (
            scan_id="scan-123",
            target_url="https://hackerone.com",
            nmap_data={},
            tls_data={},
        )

    assert result["status"] == "completed"
    assert result["scan_id"] == "scan-123"
    assert result["source_name"] == "fingerprint"

    assert len(result["technologies"]) == 1

    technology = result["technologies"][0]
    assert technology["technology_type"] == "unknown"
    assert technology["product"] == "nginx"
    assert technology["confidence"] == 0.40
    assert technology["evidence"]["vendor"] == "f5"
    assert technology["evidence"]["target_url"] == "https://hackerone.com"

    assert mock_callback.call_count == 2
    mock_callback.assert_any_call(
            scan_id="scan-123",
            source_name="fingerprint",
            status="completed",
            raw_result=fake_fingerprint_results,
            findings=[],
            assets=[],
            services=[],
            technologies=result["technologies"],
            error_message=None,
        )


@patch("app.tasks.fingerprinting_task.celery_app.send_task")
@patch("app.tasks.fingerprinting_task.send_source_callback")
@patch("app.tasks.fingerprinting_task.FingerprintingService")
def test_run_fingerprinting_scan_task_empty(mock_service_class, mock_callback, mock_send_task):
    mock_service_instance = MagicMock()
    mock_service_class.return_value = mock_service_instance

    fake_fingerprint_results = \
        {
            "fingerprint":
                {
                    "software": []
                }
        }

    mock_service_instance.run.return_value = fake_fingerprint_results

    result = run_fingerprinting_scan_task.run \
            (
            scan_id="scan-123",
            target_url="https://hackerone.com",
            nmap_data={},
            tls_data={},
        )

    assert result["status"] == "completed"
    assert result["assets"] == []


@patch("app.tasks.fingerprinting_task.send_source_callback")
@patch("app.tasks.fingerprinting_task.FingerprintingService")
def test_run_fingerprinting_scan_task_failure(mock_service_class, mock_callback):
    mock_service_instance = MagicMock()
    mock_service_class.return_value = mock_service_instance
    mock_service_instance.run.side_effect = Exception("Connection timed out")

    result = run_fingerprinting_scan_task.run \
            (
            scan_id="scan-456",
            target_url="https://hackerone.com",
            nmap_data={},
            tls_data={},
        )

    assert result["status"] == "failed"
    assert result["error_message"] == "Connection timed out"
    assert result["assets"] == []

    expected_raw_result = \
        {
            "target": "https://hackerone.com",
            "error": "Connection timed out",
        }

    assert mock_callback.call_count == 2
    mock_callback.assert_any_call(
            scan_id="scan-456",
            source_name="fingerprint",
            status="failed",
            raw_result=expected_raw_result,
            findings=[],
            assets=[],
            services=[],
            technologies=[],
            error_message="Connection timed out",
        )