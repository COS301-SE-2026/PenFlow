from unittest.mock import patch

from app.tasks.cve_task import run_cve_scan_task


@patch("app.tasks.cve_task.send_source_callback")
@patch("app.tasks.cve_task.run_cve_scan")
def test_run_cve_scan_task_success(
    mock_run_scan,
    mock_callback,
):
    #fake nvd response
    fake_vulnerabilities = \
    [
        {
            "cve_id": "CVE-2025-1234",
            "severity": "HIGH",
            "description": "Example vulnerability.",
            "remediation": "Apply the latest patch.",
            "affected_software": "cpe:2.3:a:f5:nginx:1.18.0:*:*:*:*:*:*:*",
            "cvss_score": 8.8,
        }
    ]

    mock_run_scan.return_value = fake_vulnerabilities

    result = run_cve_scan_task.run\
    (
        scan_id="scan-123",
        resolved_inventory=[],
    )

    assert result["status"] == "completed"
    assert result["scan_id"] == "scan-123"
    assert result["source_name"] == "cve"
    assert len(result["findings"]) == 1
    assert result["assets"] == []

    finding = result["findings"][0]

    assert finding["severity"] == "high"
    assert finding["cve_id"] == "CVE-2025-1234"
    assert finding["cvss_score"] == 8.8

    assert mock_callback.call_count == 2
    mock_callback.assert_any_call(
        scan_id="scan-123",
        source_name="cve",
        status="completed",
        raw_result=
        {
            "vulnerabilities": fake_vulnerabilities,
        },
        findings=result["findings"],
        assets=[],
        services=[],
        technologies=[],
        error_message=None,
    )


@patch("app.tasks.cve_task.send_source_callback")
@patch("app.tasks.cve_task.run_cve_scan")
def test_run_cve_scan_task_empty(
    mock_run_scan,
    mock_callback,
):
    #no NVD response
    mock_run_scan.return_value = []

    result = run_cve_scan_task.run\
    (
        scan_id="scan-123",
        resolved_inventory=[],
    )

    assert result["status"] == "completed"
    assert result["findings"] == []
    assert result["assets"] == []

    assert mock_callback.call_count == 2


@patch("app.tasks.cve_task.send_source_callback")
@patch("app.tasks.cve_task.run_cve_scan")
def test_run_cve_scan_task_failure(
    mock_run_scan,
    mock_callback,
):
    mock_run_scan.side_effect = Exception("NVD unavailable")

    result = run_cve_scan_task.run\
    (
        scan_id="scan-456",
        resolved_inventory=[],
    )

    assert result["status"] == "failed"
    assert result["error_message"] == "NVD unavailable"
    assert result["findings"] == []
    assert result["assets"] == []

    assert mock_callback.call_count == 2
    mock_callback.assert_any_call(
        scan_id="scan-456",
        source_name="cve",
        status="failed",
        raw_result=
        {
            "error": "NVD unavailable",
        },
        findings=[],
        assets=[],
        services=[],
        technologies=[],
        error_message="NVD unavailable",
    )