from unittest.mock import patch
from app.tasks.domain_verification_task import run_domain_verification


# happy path [Verification successful] [Token not found]

#verificatiojn success
@patch("app.tasks.domain_verification_task.send_source_callback")
@patch("app.tasks.domain_verification_task.verify_txt_record")
def test_domain_verification_success(
    mock_verify,
    mock_send_callback,
):
    """
    Returns a completed result when the verification service succeeds.
    """

    mock_verify.return_value = True
    result = run_domain_verification(
        "scan-123",
        "hackerone.com",
        "penflow-verify=abc123",
    )
    assert result == {
        "scan_id": "scan-123",
        "source_name": "domain_verification",
        "status": "completed",
        "raw_result": {
            "domain": "hackerone.com",
            "verified": True,
        },
        #no findings on verificatin
        "findings": [],
        "assets": [],
    }

    mock_verify.assert_called_once_with(
        "hackerone.com",
        "penflow-verify=abc123",
    )

    mock_send_callback.assert_called_once_with(
        scan_id="scan-123",
        source_name="domain_verification",
        status="completed",
        raw_result={
            "domain": "hackerone.com",
            "verified": True,
        },
        findings=[],
        assets=[],
        error_message=None,
    )

#token not found
@patch("app.tasks.domain_verification_task.send_source_callback")
@patch("app.tasks.domain_verification_task.verify_txt_record")
def test_domain_verification_token_not_found(
    mock_verify,
    mock_send_callback,
):
    """
    Worker still completes when the token is not found.
    The backend decides what to do with verified=False.
    """

    mock_verify.return_value = False

    result = run_domain_verification(
        "scan-123",
        "hackerone.com",
        "penflow-verify=abc123",
    )

    assert result["status"] == "completed"
    assert result["raw_result"]["verified"] is False

    mock_send_callback.assert_called_once()


# sad paths [Verification service]

#Verification service
@patch("app.tasks.domain_verification_task.send_source_callback")
@patch("app.tasks.domain_verification_task.verify_txt_record")
def test_domain_verification_service_exception(
    mock_verify,
    mock_send_callback,
):
    """
    Returns a failed result when the verification service crashes.
    """

    mock_verify.side_effect = Exception("DNS lookup exploded")
    result = run_domain_verification(
        "scan-123",
        "hackerone.com",
        "penflow-verify=abc123",
    )
    assert result == {
        "scan_id": "scan-123",
        "source_name": "domain_verification",
        "status": "failed",
        "raw_result": {
            "error": "DNS lookup exploded",
        },
        "findings": [],
        "assets": [],
        "error_message": "DNS lookup exploded",
    }

    mock_send_callback.assert_called_once_with(
        scan_id="scan-123",
        source_name="domain_verification",
        status="failed",
        raw_result={
            "error": "DNS lookup exploded",
        },
        findings=[],
        assets=[],
        error_message="DNS lookup exploded",
    )