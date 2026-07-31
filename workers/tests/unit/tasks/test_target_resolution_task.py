from unittest.mock import patch

from app.tasks.target_resolution_task import run_target_resolution

#happy paths

# Happy Path 1 [IPv4 and IPv6]
@patch("app.tasks.target_resolution_task.celery_app.send_task")
@patch("app.tasks.target_resolution_task.send_source_callback")
@patch("app.tasks.target_resolution_task.resolve_target_ips")
def test_run_target_resolution_success(
    mock_resolve,
    mock_callback,
    mock_send_task,
):
    """
    Returns a completed result when we have a domain that can be
    reached and both ipv4 and 6 address exist at the domain we are targeting.
    """
    mock_resolve.return_value = {
        "ipv4": ["104.26.12.5"],
        "ipv6": ["2606:4700::1"],
    }

    result = run_target_resolution(
        "scan-123",
        "hackerone.com",
    )

    expected_assets = [
        {
            "identifier": "104.26.12.5",
            "asset_type": "ipv4",
            "asset_metadata": {
                "source_domain": "hackerone.com"
            }
        },
        {
            "identifier": "2606:4700::1",
            "asset_type": "ipv6",
            "asset_metadata": {
                "source_domain": "hackerone.com"
            }
        },
    ]

    assert result == {
        "scan_id": "scan-123",
        "source_name": "target_resolution",
        "status": "completed",
        "raw_result": {
            "ipv4": ["104.26.12.5"],
            "ipv6": ["2606:4700::1"],
        },
        "findings": [],
        "services": [],
        "technologies": [],
        "assets": expected_assets,
    }

    mock_resolve.assert_called_once_with("hackerone.com")

    mock_callback.assert_called_once_with(
        scan_id="scan-123",
        source_name="target_resolution",
        status="completed",
        raw_result={
            "ipv4": ["104.26.12.5"],
            "ipv6": ["2606:4700::1"],
        },
        findings=[],
        services=[],
        technologies=[],
        assets=expected_assets,
        error_message=None,
    )

    mock_send_task.assert_called_once_with(
        "scan.phase2_nmap",
        args=["scan-123", "104.26.12.5", "hackerone.com"]
    )


# Happy Path 2 [IPv4 only]
@patch("app.tasks.target_resolution_task.celery_app.send_task")
@patch("app.tasks.target_resolution_task.send_source_callback")
@patch("app.tasks.target_resolution_task.resolve_target_ips")
def test_run_target_resolution_ipv4_only(
    mock_resolve,
    mock_callback,
    mock_send_task,
):
    """
    Returning only the ipv4 results cause either ipv6 doesnt exist or fails
    """
    mock_resolve.return_value = {
        "ipv4": ["104.26.12.5"],
        "ipv6": [],
    }

    result = run_target_resolution(
        "scan-123",
        "hackerone.com",
    )

    expected_assets = [
        {
            "identifier": "104.26.12.5",
            "asset_type": "ipv4",
            "asset_metadata": {
                "source_domain": "hackerone.com"
            }
        }
    ]

    assert result == {
        "scan_id": "scan-123",
        "source_name": "target_resolution",
        "status": "completed",
        "raw_result": {
            "ipv4": ["104.26.12.5"],
            "ipv6": [],
        },
        "findings": [],
        "services": [],
        "technologies": [],
        "assets": expected_assets,
    }

    mock_callback.assert_called_once()

    mock_send_task.assert_called_once_with(
        "scan.phase2_nmap",
        args=["scan-123", "104.26.12.5", "hackerone.com"]
    )


# Happy Path 3 [IPv6 only]

@patch("app.tasks.target_resolution_task.celery_app.send_task")
@patch("app.tasks.target_resolution_task.send_source_callback")
@patch("app.tasks.target_resolution_task.resolve_target_ips")
def test_run_target_resolution_ipv6_only(
    mock_resolve,
    mock_callback,
    mock_send_task,
):
    """
    Returning only the ipv6 results cause either ipv4 doesnt exist or fails
    """
    mock_resolve.return_value = {
        "ipv4": [],
        "ipv6": ["2606:4700::1"],
    }

    result = run_target_resolution(
        "scan-123",
        "hackerone.com",
    )

    expected_assets = [
        {
            "identifier": "2606:4700::1",
            "asset_type": "ipv6",
            "asset_metadata": {
                "source_domain": "hackerone.com"
            }
        }
    ]

    assert result == {
        "scan_id": "scan-123",
        "source_name": "target_resolution",
        "status": "completed",
        "raw_result": {
            "ipv4": [],
            "ipv6": ["2606:4700::1"],
        },
        "findings": [],
        "services": [],
        "technologies": [],
        "assets": expected_assets,
    }

    mock_callback.assert_called_once()

    mock_send_task.assert_not_called()


#Sad paths

# Sad Path 1 [No IP addresses]
@patch("app.tasks.target_resolution_task.celery_app.send_task")
@patch("app.tasks.target_resolution_task.send_source_callback")
@patch("app.tasks.target_resolution_task.resolve_target_ips")
def test_run_target_resolution_no_ips(
    mock_resolve,
    mock_callback,
    mock_send_task,
):
    """
    Returning empty results because no ipv4 or 6 address's can bve found at the target domain
    """

    mock_resolve.return_value = {
        "ipv4": [],
        "ipv6": [],
    }

    result = run_target_resolution(
        "scan-123",
        "hackerone.com",
    )

    assert result == {
        "scan_id": "scan-123",
        "source_name": "target_resolution",
        "status": "failed",
        "raw_result": {
            "ipv4": [],
            "ipv6": [],
        },
        "findings": [],
        "assets": [],
        "technologies": [],
        "services": [],
        "error_message": "No IPv4 or IPv6 addresses were resolved.",
    }

    mock_callback.assert_called_once_with(
        scan_id="scan-123",
        source_name="target_resolution",
        status="failed",
        raw_result={
            "ipv4": [],
            "ipv6": [],
        },
        findings=[],
        assets=[],
        services=[],
        technologies=[],
        error_message="No IPv4 or IPv6 addresses were resolved.",
    )

    mock_send_task.assert_not_called()


# Sad Path 2 [Service Exception]
@patch("app.tasks.target_resolution_task.celery_app.send_task")
@patch("app.tasks.target_resolution_task.send_source_callback")
@patch("app.tasks.target_resolution_task.resolve_target_ips")
def test_run_target_resolution_exception(
    mock_resolve,
    mock_callback,
    mock_send_task,
):
    """
    Returns this when an unexpected from the norm exception arrises
    """

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
        "findings": [],
        "assets": [],
        "services": [],
        "technologies": [],
        "error_message": "DNS exploded",
    }

    mock_callback.assert_called_once_with(
        scan_id="scan-123",
        source_name="target_resolution",
        status="failed",
        raw_result={
            "error": "DNS exploded",
        },
        findings=[],
        assets=[],
        services=[],
        technologies=[],
        error_message="DNS exploded",
    )
    mock_send_task.assert_not_called()