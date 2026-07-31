from unittest.mock import patch

from app.tasks.tls_task import run_tls_scan_task


##Happy Paths [Successful Scan]
@patch("app.tasks.tls_task.send_source_callback")
@patch("app.tasks.tls_task.run_tls_scan")
def test_successful_tls_scan\
(
    mock_scan,
    mock_callback,
):
    """
    Successfully processes a TLS scan.
    """

    mock_scan.return_value = \
    {
        "targets":
        [
            {
                "port": 443,
                "tls_version": "TLSv1.3",
                "cipher":
                (
                    "TLS_AES_256_GCM_SHA384",
                    "TLSv1.3",
                    256,
                ),
                "certificate":
                {
                    "subject":
                    {
                        "commonName": "hackerone.com",
                    },
                    "issuer":
                    {
                        "organizationName": "The Brozz",
                    },
                    "valid_from": "today",
                    "valid_until": "2035",
                    "expired": False,
                    "self_signed": False,
                },
            }
        ]
    }

    result = run_tls_scan_task.run\
    (
        scan_id="scan123",
        ip_address="1.1.1.1",
        hostname="hackerone.com",
        ports=[],
    )

    assert result["status"] == "completed"
    assert result["findings"] == []
    assert result["assets"] == []

    mock_callback.assert_called_once()


##Sad Paths [Expired Certificate]
@patch("app.tasks.tls_task.send_source_callback")
@patch("app.tasks.tls_task.run_tls_scan")
def test_expired_certificate\
(
    mock_scan,
    mock_callback,
):
    """
    Generates a finding for an expired certificate.
    """

    mock_scan.return_value = \
    {
        "targets":
        [
            {
                "port": 443,
                "tls_version": "TLSv1.3",
                "cipher":
                (
                    "TLS_AES_256_GCM_SHA384",
                    "TLSv1.3",
                    256,
                ),
                "certificate":
                {
                    "subject": {},
                    "issuer": {},
                    "valid_from": "2020",
                    "valid_until": "2021",
                    "expired": True,
                    "self_signed": False,
                },
            }
        ]
    }

    result = run_tls_scan_task.run\
    (
        scan_id="scan123",
        ip_address="1.1.1.1",
        hostname="hackerone.com",
        ports=[],
    )

    assert len(result["findings"]) == 1

    assert \
    (
        result["findings"][0]["title"]
        == "Expired TLS Certificate"
    )


#[Handshake Failure]
@patch("app.tasks.tls_task.send_source_callback")
@patch("app.tasks.tls_task.run_tls_scan")
def test_tls_handshake_failure\
(
    mock_scan,
    mock_callback,
):
    """
    Generates a finding when the TLS handshake fails.
    """

    mock_scan.return_value = \
    {
        "targets":
        [
            {
                "port": 443,
                "error": "TLS handshake failed",
            }
        ]
    }

    result = run_tls_scan_task.run\
    (
        scan_id="scan123",
        ip_address="1.1.1.1",
        hostname="hackerone.com",
        ports=[],
    )

    assert len(result["findings"]) == 1

    assert \
    (
        result["findings"][0]["title"]
        == "TLS Handshake Failed"
    )


#[Failed Response]
@patch("app.tasks.tls_task.send_source_callback")
@patch("app.tasks.tls_task.run_tls_scan")
def test_failed_tls_scan\
(
    mock_scan,
    mock_callback,
):
    """
    Returns a failed result when the service raises an exception.
    """

    mock_scan.side_effect = Exception\
    (
        "Unexpected TLS failure"
    )

    result = run_tls_scan_task.run\
    (
        scan_id="scan123",
        ip_address="1.1.1.1",
        hostname="hackerone.com",
        ports=[],
    )

    assert result["status"] == "failed"

    assert \
    (
        "Unexpected TLS failure"
        in result["error_message"]
    )

    mock_callback.assert_called_once()