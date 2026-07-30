from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.base import ScanType
from app.services.report_service import (
    build_report_output_path,
    queue_report_generation,
    render_report_html,
)


def test_build_report_output_path(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.report_service.REPORT_OUTPUT_DIR", tmp_path)

    result = build_report_output_path("scan-1234")
    
    assert result == tmp_path / "penflow_report_scan-1234.pdf"
    assert tmp_path.exists()


#phase2 view report happy path:
#render html
@patch("app.services.report_service.get_template_environment")
def test_render_report_html(mock_get_template_environment):
    template = MagicMock()
    template.render.return_value = "<html>Test</html>"
    env = MagicMock()
    env.get_template.return_value = template
    mock_get_template_environment.return_value = env

    result = render_report_html(ScanType.PASSIVE_CTEM, {"domain": "test.com"})

    assert result == "<html>Test</html>"
    env.get_template.assert_called_once()
    template.render.assert_called_once_with(domain="test.com")


@pytest.mark.asyncio
@patch("app.services.report_service.mark_report_task_queued", new_callable=AsyncMock)
@patch("app.services.report_service.mark_report_generating", new_callable=AsyncMock)
@patch("app.services.report_service.load_report_data", new_callable=AsyncMock)
@patch("app.services.report_service.build_report_context")
@patch("app.services.report_service.render_report_html")
@patch("app.services.report_service.build_report_output_path")
async def test_queue_report_generation_success(
    mock_output_path,
    mock_render_html,
    mock_build_context,
    mock_load_report_data,
    mock_mark_generating,
    mock_mark_task_queued,
    tmp_path,
):
    db = AsyncMock()
    pdf_path = tmp_path / "report.pdf"

    mock_output_path.return_value = pdf_path
    mock_render_html.return_value = "<html>Test</html>"
    mock_build_context.return_value = {"domain": "test.com"}
    mock_load_report_data.return_value = {
        "scan": MagicMock(),
        "findings": [],
        "scan_sources": []
    }

    simulated_task = MagicMock()
    simulated_task.id = "task-1234"

    with patch("app.services.report_service.celery_app.send_task", return_value=simulated_task):
        result = await queue_report_generation(db, "scan-1234")
    
    assert result["scan_id"] == "scan-1234"
    assert result["task_id"] == "task-1234"
    assert result["status"] == "generating"
    mock_mark_task_queued.assert_awaited_once()
