from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from uuid import uuid4
from app.models.base import ScanType
from app.services.report_service import (
    build_report_output_path,
    queue_report_generation,
    render_report_html,
)


def test_build_report_output_path(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.report_service.REPORT_OUTPUT_DIR", tmp_path)

    scan_id = str(uuid4())
    result = build_report_output_path(scan_id)
    
    assert result == tmp_path / f"penflow_report_{scan_id}.pdf"
    assert tmp_path.exists()


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
@patch("app.services.report_service.mark_report_failed", new_callable=AsyncMock)
@patch("app.services.report_service.mark_report_generating", new_callable=AsyncMock)
async def test_generate_report_pdf_fail(mock_mark_generating, mock_mark_failed):
    db = AsyncMock()
    scan_id = str(uuid4())
    with patch("app.services.report_service.load_report_data", side_effect=Exception("failure")):
        with pytest.raises(Exception, match="failure"):
            await queue_report_generation(db, scan_id)

    mock_mark_failed.assert_awaited_once()


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
    scan_id = str(uuid4())
    pdf_path = tmp_path / "report.pdf"

    scan = MagicMock()
    scan.scan_type = ScanType.PASSIVE_CTEM

    mock_output_path.return_value = pdf_path
    mock_render_html.return_value = "<html>Test</html>"
    mock_build_context.return_value = {"domain": "test.com"}
    mock_load_report_data.return_value = {
        "scan": scan,
        "findings": [],
        "scan_sources": []
    }

    simulated_task = MagicMock()
    simulated_task.id = "task-1234"

    with patch("app.services.report_service.celery_app.send_task", return_value=simulated_task):
        result = await queue_report_generation(db, scan_id)
    
    assert result["scan_id"] == scan_id
    assert result["task_id"] == "task-1234"
    assert result["status"] == "generating"
    mock_mark_task_queued.assert_awaited_once()