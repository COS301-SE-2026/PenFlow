from unittest.mock import MagicMock, patch

from app.queue.celery_app import health_check
from app.tasks.wappalyzer_tasks import run_wappalyzer
from app.tasks.target_resolution_task import run_target_resolution
from app.tasks.nmap_task import run_nmap_scan
from app.tasks.http_security_task import run_http_security_scan_task
from app.tasks.tls_task import run_tls_scan_task
from app.tasks.fingerprinting_task import run_fingerprinting_scan_task
from app.tasks.cpe_resolver_task import run_cpe_resolver_task


@patch("app.tasks.wappalyzer_tasks.send_source_callback")
def test_wappalyzer_task_mock_mode(mock_callback):
    result = run_wappalyzer.delay(
        "test-scan-id",
        "hackerone.com",
    ).get()

    assert result["scan_id"] == "test-scan-id"
    assert result["source_name"] == "wappalyzer"
    assert "raw_result" in result
    assert "findings" in result
    mock_callback.assert_called_once()

def test_worker_health_check():
    result = health_check.delay().get()

    assert result == "Worker is alive"

#mock the dns part, for this section we only care
#about worker component interactions
def create_mock_dns_answer(ip_records: list[str]) -> MagicMock:
    records = []

    for ip in ip_records:
        record = MagicMock()
        record.to_text.return_value = ip
        records.append(record)

    answer = MagicMock()
    answer.__iter__.return_value = records
    return answer




#phase2 workers

#Target Resolution int test
@patch("app.tasks.target_resolution_task.celery_app.send_task")
@patch("app.tasks.target_resolution_task.send_source_callback")
@patch("app.services.target_resolution_service.dns.resolver.Resolver.resolve")

def test_target_resolution_task_service_pipeline\
(
    mock_resolve,
    mock_callback,
    mock_send_task,
):
    def dns_side_effect(domain, record_type):
        if record_type == "A":
            return create_mock_dns_answer\
            (
                [
                    "192.168.1.1",
                ]
            )

        if record_type == "AAAA":
            return create_mock_dns_answer\
            (
                [
                    "2001:0df8:00f2::06ee:0000:0f11",
                ]
            )

    mock_resolve.side_effect = dns_side_effect

    result = run_target_resolution\
    (
        "scan-123",
        "hackerone.com",
    )

    assert result["status"] == "completed"

    assert result["raw_result"] == \
    {
        "ipv4": \
        [
            "192.168.1.1",
        ],
        "ipv6": \
        [
            "2001:0df8:00f2::06ee:0000:0f11",
        ],
    }

    mock_callback.assert_called_once()

    mock_send_task.assert_called_once_with(
        "scan.phase2_nmap",
        args=\
        [
            "scan-123",
            "192.168.1.1",
            "hackerone.com",
        ],
    )

    assert mock_resolve.call_count == 2

#nmap int test
@patch("app.tasks.nmap_task.celery_app.send_task")
@patch("app.tasks.nmap_task.send_source_callback")
@patch("app.services.nmap_service.nmap.PortScanner")
def test_nmap_task_service_pipeline\
(
    mock_portscanner,
    mock_callback,
    mock_send_task,
):
    # Fake Nmap scanner

    scanner = MagicMock()
    scanner.all_hosts.return_value = \
    [
        "192.168.1.1",
    ]

    host = MagicMock()
    host.state.return_value = "up"
    host.__contains__.side_effect = lambda key: key in ["hostnames", "tcp"]
    host.__getitem__.side_effect = lambda key: \
    {
        "hostnames": \
        [
            {
                "name": "hackerone.com",
            }
        ],
        "tcp": \
        {
            443: \
            {
                "state": "open",
                "name": "https",
                "product": "nginx",
                "version": "1.27.0",
                "extrainfo": None,
            }
        },
    }[key]

    scanner.__getitem__.return_value = host
    mock_portscanner.return_value = scanner

    # Run the Real task
    result = run_nmap_scan\
    (
        "scan-123",
        "192.168.1.1",
        "hackerone.com",
    )

    # Assertions
    assert result["status"] == "completed"
    assert result["raw_result"]["status"] == "up"
    assert len(result["raw_result"]["ports"]) == 1
    assert result["raw_result"]["ports"][0]["port"] == 443
    assert result["raw_result"]["ports"][0]["service"] == "https"
    assert result["raw_result"]["ports"][0]["product"] == "nginx"

    # Callback should be triggered
    mock_callback.assert_called_once()

    # mocking 3 ip address arrivals
    assert mock_send_task.call_count == 3

    mock_send_task.assert_any_call\
    (
        "scan.phase2_tls",
        args=\
        [
            "scan-123",
            "192.168.1.1",
            result["raw_result"]["ports"],
            "hackerone.com",
        ],
    )

    mock_send_task.assert_any_call\
    (
        "scan.phase2_http_security",
        args=\
        [
            "scan-123",
            "hackerone.com",
            "192.168.1.1",
            result["raw_result"]["ports"],
        ],
    )

    mock_send_task.assert_any_call\
    (
        "scan.phase2_fingerprint",
        args=\
        [
            "scan-123",
            "https://hackerone.com",
            result["raw_result"],
            None,
        ],
    )
    mock_portscanner.assert_called_once()
    scanner.scan.assert_called_once()

#http security int test
@patch("app.tasks.http_security_task.send_source_callback")
@patch("app.services.http_security_service.requests.get")
def test_http_security_task_service_pipeline\
(
    mock_get,
    mock_callback,
):
    response = MagicMock()
    response.status_code = 200
    response.headers = \
    {
        "Server": "nginx",
        "Strict-Transport-Security": "max-age=696969",
        "Content-Security-Policy": "default-src 'self'",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin",
        "Permissions-Policy": "geolocation=()",
        "X-Content-Type-Options": "nosniff",
    }

    mock_get.return_value = response
    ports = \
    [
        {
            "port": 443,
            "service": "https",
        }
    ]

    result = run_http_security_scan_task\
    (
        "scan-123",
        "hackerone.com",
        "192.168.1.1",
        ports,
    )

    assert result["status"] == "completed"
    assert len(result["raw_result"]["targets"]) == 1
    target = result["raw_result"]["targets"][0]
    assert target["url"] == "https://hackerone.com"
    assert target["status_code"] == 200
    assert target["server"] == "nginx"
    assert target["security_headers"]["strict_transport_security"] == "max-age=696969"
    assert target["security_headers"]["content_security_policy"] == "default-src 'self'"
    assert result["findings"] == []
    mock_callback.assert_called_once()
    mock_get.assert_called_once()


#TLS int test
#mock the handshake required in this stage
@patch("app.tasks.tls_task.send_source_callback")
@patch("app.services.tls_service.os.unlink")
@patch("app.services.tls_service.ssl._ssl._test_decode_cert")
@patch("app.services.tls_service.tempfile.NamedTemporaryFile")
@patch("app.services.tls_service.ssl.DER_cert_to_PEM_cert")
@patch("app.services.tls_service.ssl.create_default_context")
@patch("app.services.tls_service.socket.create_connection")
def test_tls_task_service_pipeline\
(
    mock_connection,
    mock_context,
    mock_der_to_pem,
    mock_tempfile,
    mock_decode,
    mock_unlink,
    mock_callback,
):

    # Fake TCP connection and tls sockets
    socket_connection = MagicMock()
    mock_connection.return_value.__enter__.return_value = socket_connection
    tls_socket = MagicMock()
    tls_socket.version.return_value = "TLSv1.3"
    tls_socket.cipher.return_value = \
    (
        "TLS_AES_256_GCM_SHA384",
        "TLSv1.3",
        256,
    )

    tls_socket.getpeercert.return_value = b"fake-binary-cert"

    # Fake SSL Context
    context = MagicMock()
    context.wrap_socket.return_value.__enter__.return_value = tls_socket
    mock_context.return_value = context

    # Fake certificate conversion
    mock_der_to_pem.return_value = "certificateWOW"

    # Fake temporary certificate file
    temp_file = MagicMock()
    temp_file.name = "/tmp/mockfake.txt"
    mock_tempfile.return_value.__enter__.return_value = temp_file

    # Fake decoded certificate
    mock_decode.return_value = \
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
                ("commonName", "Let's Encrypt YAY"),
            ),
        ),
        "notBefore": "Jan 01 00:00:00 2026 GMT",
        "notAfter": "Jan 01 00:00:00 2030 GMT",
    }

    # Fake Nmap ports passed into TLS worker
    ports = [
        {
            "port": 443,
            "service": "https",
        }
    ]

    # Run the REAL task
    result = run_tls_scan_task(
        "scan-123",
        "192.168.1.1",
        ports,
        "hackerone.com",
    )

    assert result["status"] == "completed"
    assert result["raw_result"]["ip"] == "192.168.1.1"
    assert len(result["raw_result"]["targets"]) == 1
    target = result["raw_result"]["targets"][0]
    assert target["port"] == 443
    assert target["tls_version"] == "TLSv1.3"
    assert target["cipher"] == \
    (
        "TLS_AES_256_GCM_SHA384",
        "TLSv1.3",
        256,
    )

    assert (target["certificate"]["subject"] ==
    {
        "commonName": "hackerone.com",
    })
    assert target["certificate"]["issuer"] == \
    {
        "commonName": "Let's Encrypt YAY",
    }
    assert target["certificate"]["expired"] is False
    assert target["certificate"]["self_signed"] is False
    mock_callback.assert_called_once()
    mock_connection.assert_called_once()
    mock_context.assert_called_once()
    context.wrap_socket.assert_called_once()
    tls_socket.getpeercert.assert_called_once()
    mock_decode.assert_called_once()
    mock_unlink.assert_called_once()


#fingerprinting int test
@patch("app.tasks.fingerprinting_task.celery_app.send_task")
@patch("app.tasks.fingerprinting_task.send_source_callback")
@patch("app.services.fingerprinting_service.requests.get")
def test_fingerprinting_task_service_pipeline\
(
    mock_get,
    mock_callback,
    mock_send_task,
):
    response = MagicMock()
    response.status_code = 200
    response.url = "https://hackerone.com"
    response.headers = \
    {
        "Server": "nginx/1.27.0",
        "Content-Security-Policy": "default-src 'self'",
        "X-Powered-By": "PHP/8.2",
    }

    #the type of response we expect
    response.cookies.get_dict.return_value = {}
    response.text = """
    <html>
        <head>
            <meta name="generator" content="WordPress 6.8">
            <title>HackerOne</title>
        </head>

        <body>

            <script src="/wp-content/test.js"></script>

        </body>

    </html>
    """

    mock_get.return_value = response

    # Real task
    result = run_fingerprinting_scan_task(
        "scan-123",
        "https://hackerone.com",
        {"ports": \
                [
                    {
                        "product": "nginx",
                        "version": "1.27.0",
                    }
                ]
            },
        {
            "targets": \
            [
                {
                    "certificate": \
                    {
                        "issuer": \
                        {
                            "organizationName": "Cloudflare Inc",
                        }
                    }
                }
            ]
        },
    )
    assert result["status"] == "completed"
    assert result["source_name"] == "fingerprint"
    assert "fingerprint" in result["raw_result"]
    assert len(result["assets"]) > 0
    mock_callback.assert_called_once()
    mock_send_task.assert_called_once()
    #cpe need to be called immediately to generate
    mock_send_task.assert_called_with(
        "scan.phase2_cpe_resolver",
        args=\
        [
            "scan-123",
            result["raw_result"]["fingerprint"]["software"],
        ],
    )
    mock_get.assert_called_once()



#cpe resolver int test
@patch("app.tasks.cpe_resolver_task.celery_app.send_task")
@patch("app.tasks.cpe_resolver_task.send_source_callback")
def test_cpe_resolver_task_service_pipeline\
(
    mock_callback,
    mock_send_task,
):
    software_inventory = \
    [
        {
            "vendor": "unknown",
            "product": "nginx",
            "version": "1.27.0",
            "confidence": "high",
        },
        {
            "vendor": "unknown",
            "product": "mysql",
            "version": "8.0.42",
            "confidence": "high",
        },
    ]

    result = run_cpe_resolver_task\
    (
        "scan-123",
        software_inventory,
    )

    assert result["status"] == "completed"
    assert result["source_name"] == "cpe_resolver"
    resolved = result["raw_result"]["resolved_inventory"]
    assert len(resolved) == 2
    assert resolved[0]["vendor"] == "nginx"
    assert resolved[0]["product"] == "nginx"
    assert resolved[0]["cpe"] == \
        "cpe:2.3:a:nginx:nginx:1.27.0:*:*:*:*:*:*:*"
    assert resolved[1]["vendor"] == "oracle"
    assert resolved[1]["product"] == "mysql"
    assert resolved[1]["cpe"] == \
        "cpe:2.3:a:oracle:mysql:8.0.42:*:*:*:*:*:*:*"

    mock_callback.assert_called_once()
    #similarly to fingerprinting, we need to call cve from this result
    mock_send_task.assert_called_once_with\
    (
        "scan.phase2_cve",
        args=\
        [
            "scan-123",
            resolved,
        ],
    )