from unittest.mock import patch

import pytest

from app.tasks.target_resolution_task import run_target_resolution


@pytest.mark.parametrize(
    ("ipv4", "ipv6"),
    [
        (["104.26.12.5"], ["2606:4700::1"]),
        (["104.26.12.5"], []),
        ([], ["2606:4700::1"]),
    ],
)
@patch("app.tasks.target_resolution_task.celery_app.send_task")
@patch("app.tasks.target_resolution_task.send_source_callback")
@patch("app.tasks.target_resolution_task.resolve_target_scope")
def test_run_target_resolution_success(
    mock_resolve,
    mock_callback,
    mock_send_task,
    ipv4,
    ipv6,
):

    addresses = [*ipv4, *ipv6]

    resolved_scope = {
        "targets": [
            {
                "hostname": "hackerone.com",
                "ipv4": ipv4,
                "ipv6": ipv6,
            }
        ],
        "ip_to_hostnames": {
            address: ["hackerone.com"]
            for address in addresses
        },
    }

    mock_resolve.return_value = resolved_scope

    result = run_target_resolution(
        "scan-123",
        "hackerone.com",
    )

    expected_assets = [
        {
            "identifier": address,
            "asset_type": (
                "ipv4"
                if address in ipv4
                else "ipv6"
            ),
            "asset_metadata": {
                "source_domain": "hackerone.com",
                "hostnames": ["hackerone.com"],
                "ip_version": (
                    4
                    if address in ipv4
                    else 6
                ),
                "resolution_source": "dns",
            },
        }
        for address in addresses
    ]

    assert result == {
        "scan_id": "scan-123",
        "source_name": "target_resolution",
        "status": "completed",
        "raw_result": resolved_scope,
        "assets": expected_assets,
        "services": [],
        "technologies": [],
        "findings": [],
    }

    mock_resolve.assert_called_once_with(
        ["hackerone.com"],
    )

    mock_callback.assert_any_call(
        scan_id="scan-123",
        source_name="target_resolution",
        status="completed",
        raw_result=resolved_scope,
        assets=expected_assets,
        services=[],
        technologies=[],
        findings=[],
        error_message=None,
    )

    mock_send_task.assert_called_once_with(
        "scan.phase2_nmap",
        args=[
            "scan-123",
            resolved_scope["targets"],
        ],
    )


@patch("app.tasks.target_resolution_task.celery_app.send_task")
@patch("app.tasks.target_resolution_task.send_source_callback")
@patch("app.tasks.target_resolution_task.resolve_target_scope")
def test_run_target_resolution_no_ips(
    mock_resolve,
    mock_callback,
    mock_send_task,
):

    resolved_scope = {
        "targets": [
            {
                "hostname": "hackerone.com",
                "ipv4": [],
                "ipv6": [],
            }
        ],
        "ip_to_hostnames": {},
    }

    mock_resolve.return_value = resolved_scope

    result = run_target_resolution(
        "scan-123",
        "hackerone.com",
    )

    assert result["status"] == "failed"
    assert result["raw_result"] == resolved_scope
    assert result["error_message"] == (
        "No public IPv4 or IPv6 addresses were resolved."
    )

    mock_send_task.assert_not_called()

    mock_callback.assert_any_call(
        scan_id="scan-123",
        source_name="nmap",
        status="skipped",
        raw_result={
            "reason": "No public scan targets were resolved.",
        },
    )


@patch("app.tasks.target_resolution_task.celery_app.send_task")
@patch("app.tasks.target_resolution_task.send_source_callback")
@patch("app.tasks.target_resolution_task.resolve_target_scope")
def test_run_target_resolution_exception(
    mock_resolve,
    mock_callback,
    mock_send_task,
):

    mock_resolve.side_effect = Exception("DNS exploded")

    result = run_target_resolution(
        "scan-123",
        "hackerone.com",
    )

    assert result == {
        "scan_id": "scan-123",
        "source_name": "target_resolution",
        "status": "failed",
        "raw_result": {
            "error": "DNS exploded",
        },
        "assets": [],
        "services": [],
        "technologies": [],
        "findings": [],
        "error_message": "DNS exploded",
    }

    mock_send_task.assert_not_called()

    mock_callback.assert_any_call(
        scan_id="scan-123",
        source_name="target_resolution",
        status="failed",
        raw_result={
            "error": "DNS exploded",
        },
        assets=[],
        services=[],
        technologies=[],
        findings=[],
        error_message="DNS exploded",
    )