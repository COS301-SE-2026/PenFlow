import socket
import ssl
from unittest.mock import MagicMock, patch

from app.services.tls_service import run_tls_scan


#in tls worker we get byte certificate and then we save that in a file
#and then the file is decoded, here we just mock that end part
def create_mock_certificate():
    """
    Creates a fake decoded certificate
    """

    return \
    {
        "subject": \
        (
            (
                ("commonName", "hackerone.com"),
            ),
        ),
        "issuer": \
        (
            (
                ("organizationName", "The Brozz"),
            ),
        ),
        "notBefore": "Jan 01 00:00:00 2024 GMT",
        "notAfter": "Jan 01 00:00:00 2035 GMT",
    }


##Happy Paths [Valid Certificate]
@patch("app.services.tls_service.os.unlink")
@patch("app.services.tls_service.ssl._ssl._test_decode_cert")
@patch("app.services.tls_service.tempfile.NamedTemporaryFile")
@patch("app.services.tls_service.ssl.DER_cert_to_PEM_cert")
@patch("app.services.tls_service.ssl.create_default_context")
@patch("app.services.tls_service.socket.create_connection")
def test_valid_certificate\
(
    mock_socket,
    mock_context,
    mock_der,
    mock_tempfile,
    mock_decode,
    mock_unlink,
):
    """
    Successfully scans a TLS endpoint.
    """

    socket_connection = MagicMock()
    tls_socket = MagicMock()

    mock_socket.return_value.__enter__.return_value = socket_connection

    context = MagicMock()
    context.wrap_socket.return_value.__enter__.return_value = tls_socket
    mock_context.return_value = context

    tls_socket.version.return_value = "TLSv1.3"
    tls_socket.cipher.return_value = \
    (
        "TLS_AES_256_GCM_SHA384",
        "TLSv1.3",
        256,
    )
    tls_socket.getpeercert.return_value = b"certificate"

    mock_der.return_value = "pem"

    #mocking making the file process
    temp_file = MagicMock()
    temp_file.name = "/tmp/test.pem"
    mock_tempfile.return_value.__enter__.return_value = temp_file

    mock_decode.return_value = create_mock_certificate()

    result = run_tls_scan\
    (
        ip_address="1.1.1.1",
        hostname="hackerone.com",
        ports=\
        [
            {
                "port": 443,
                "service": "https",
            }
        ],
    )

    assert len(result["targets"]) == 1

    target = result["targets"][0]

    assert target["tls_version"] == "TLSv1.3"
    assert target["certificate"]["expired"] is False
    assert \
    (
        target["certificate"]["subject"]["commonName"]
        == "hackerone.com"
    )


##Sad Paths [Ignore Non-TLS]
def test_ignore_non_tls_ports():
    """
    Ignores services unrelated to TLS.
    """

    result = run_tls_scan\
    (
        ip_address="1.1.1.1",
        ports=\
        [
            {
                "port": 22,
                "service": "ssh",
            }
        ],
    )

    assert result["targets"] == []


#[Handshake Failure]
@patch("app.services.tls_service.socket.create_connection")
def test_tls_handshake_failure(mock_socket):
    """
    Returns an error when the handshake fails.
    """

    mock_socket.side_effect = ssl.SSLError\
    (
        "Handshake failed"
    )

    result = run_tls_scan\
    (
        ip_address="1.1.1.1",
        ports=[
            {
                "port": 443,
                "service": "https",
            }
        ],
    )

    assert len(result["targets"]) == 1
    assert "error" in result["targets"][0]


#[Timeout]
@patch("app.services.tls_service.socket.create_connection")
def test_tls_timeout(mock_socket):
    """
    Returns error when the connection times out.
    """

    mock_socket.side_effect = socket.timeout\
    (
        "Timeout"
    )

    result = run_tls_scan\
    (
        ip_address="1.1.1.1",
        ports=\
        [
            {
                "port": 443,
                "service": "https",
            }
        ],
    )

    assert len(result["targets"]) == 1
    assert "error" in result["targets"][0]