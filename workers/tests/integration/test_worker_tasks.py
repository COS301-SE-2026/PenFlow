from unittest.mock import MagicMock, patch

from app.queue.celery_app import health_check
from app.tasks.wappalyzer_tasks import run_wappalyzer
from app.tasks.target_resolution_task import run_target_resolution


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


@patch("app.tasks.target_resolution_task.celery_app.send_task")
@patch("app.tasks.target_resolution_task.send_source_callback")
@patch("app.services.target_resolution_service.dns.resolver.Resolver.resolve")
def test_target_resolution_pipeline\
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