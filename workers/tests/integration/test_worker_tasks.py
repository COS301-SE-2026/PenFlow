from unittest.mock import MagicMock, patch

from app.queue.celery_app import health_check
from app.tasks.wappalyzer_tasks import run_wappalyzer
from app.tasks.target_resolution_task import run_target_resolution
from app.tasks.nmap_task import run_nmap_scan


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