from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest 

from app.services.report_service import (
    build_report_output_path,
    check_report_task_result,
    generate_report_pdf,
    queue_report_generation,
    render_report_html,
)

def test_build_report_output_path(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.report_service.REPORT_OUTPUT_DIR", tmp_path)

    result = build_report_output_path("scan-1234")
    
    assert result == tmp_path / "ctem_report_scan-1234.pdf"
    assert tmp_path.exists()
