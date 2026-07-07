from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.routes.internal import (
    update_report_status_callback,
    update_scan_source_callback,
    update_scan_status_callback,
)

from app.models.base import ScanStatus
from app.schemas.report import ReportCallbackRequest
from app.schemas.scan import ScanCallbackRequest, ScanSourceCallbackRequest


@pytest.mark.asyncio
@patch("app.api.routes.internal.queue_report_generation", new_callable=AsyncMock)
@patch("app.api.routes.internal.ScanRepository.get_scan_by_id", new_callable=AsyncMock)
async def test_update_scan_status_completed_queues_report(mock_scan, mock_queue_report):
    scan_id = uuid4()
    db = AsyncMock()

    scan = SimpleNamespace(
        id = scan_id,
        status = ScanStatus.QUEUED,
        progress = 0,
        error_message = None,
    )

    mock_scan.return_value = scan

    mock_queue_report.return_value = {"status": "generating"}

    payload = ScanCallbackRequest(status=ScanStatus.COMPLETED)

    result = await update_scan_status_callback(scan_id, payload, db)

    assert scan.status == ScanStatus.COMPLETED
    assert scan.progress == 100
    db.commit.assert_awaited_once()
    mock_queue_report.assert_awaited_once_with(db, str(scan_id))

    assert result == {
        "scan_id": str(scan_id),
        "status": "completed",
        "report_status": "generating",
    }


@pytest.mark.asyncio
@patch("app.api.routes.internal.queue_report_generation", new_callable=AsyncMock)
@patch("app.api.routes.internal.ScanRepository.get_scan_by_id", new_callable=AsyncMock)
async def test_update_scan_status_running_does_not_queue_report(mock_scan, mock_queue_report):
    scan_id = uuid4()
    db = AsyncMock()

    scan = SimpleNamespace(
        id = scan_id,
        status = ScanStatus.QUEUED,
        progress = 0,
        error_message = None,
    )

    mock_scan.return_value = scan

    payload = ScanCallbackRequest(status=ScanStatus.RUNNING)

    result = await update_scan_status_callback(scan_id, payload, db)

    assert scan.status == ScanStatus.RUNNING
    assert scan.progress == 0

    db.commit.assert_awaited_once()
    mock_queue_report.assert_not_awaited()

    assert result == {
        "scan_id": str(scan_id),
        "status": "running",
        "report_status": None,
    }


@pytest.mark.asyncio
@patch("app.api.routes.internal.ScanRepository.get_scan_by_id", new_callable=AsyncMock)
async def test_update_scan_status_missing_scan(mock_scan):
    scan_id = uuid4()
    db = AsyncMock()

    mock_scan.return_value = None

    payload = ScanCallbackRequest(status=ScanStatus.COMPLETED)

    with pytest.raises(HTTPException) as excep:
        await update_scan_status_callback(scan_id, payload, db)

    assert excep.value.status_code == 404
    assert excep.value.detail == "Scan not found"


@pytest.mark.asyncio
@patch("app.api.routes.internal.mark_report_completed", new_callable=AsyncMock)
async def test_update_report_status_completed(mock_completed):
    scan_id = uuid4()
    db = AsyncMock()

    report = SimpleNamespace(status=SimpleNamespace(value="completed"))
    mock_completed.return_value = report

    payload = ReportCallbackRequest(
        status = "completed",
        pdf_path = "/report/report.pdf",
    )

    result = await update_report_status_callback(scan_id, payload, db)

    mock_completed.assert_awaited_once_with(
        db = db,
        scan_id = str(scan_id),
        pdf_path = "/report/report.pdf",
    )

    assert result == {
        "scan_id": str(scan_id),
        "report_status": "completed",
    }


@pytest.mark.asyncio
async def test_update_report_status_completed_needs_pdfs_path():
    scan_id = uuid4()
    db = AsyncMock()

    payload = ReportCallbackRequest(status="completed", pdf_path=None) 

    with pytest.raises(HTTPException) as excep:
        await update_report_status_callback(scan_id, payload, db)
    
    assert excep.value.status_code == 400
    assert excep.value.detail == "pdf_path is required for completed reports"


@pytest.mark.asyncio
@patch("app.api.routes.internal.mark_report_failed", new_callable=AsyncMock)
async def test_update_report_status_failed(mock_failed):
    scan_id = uuid4()
    db = AsyncMock()

    report = SimpleNamespace(status=SimpleNamespace(value="failed"))
    mock_failed.return_value = report

    payload = ReportCallbackRequest(
        status = "failed",
        error_message = "Report generation failed",
    )

    result = await update_report_status_callback(scan_id, payload, db)

    mock_failed.assert_awaited_once_with(
        db = db,
        scan_id = str(scan_id),
        error_message = "Report generation failed",
    )

    assert result == {
        "scan_id": str(scan_id),
        "report_status": "failed",
    }


@pytest.mark.asyncio
async def test_update_report_status_invalid():
    scan_id = uuid4()
    db = AsyncMock()

    result = ReportCallbackRequest(status="Incorrect Status")

    with pytest.raises(HTTPException) as excep:
        await update_report_status_callback(scan_id, result, db)

    assert excep.value.status_code == 400
    assert excep.value.detail == "Invalid report status"


@pytest.mark.asyncio
@patch("app.api.routes.internal.ScanRepository.save_source_result", new_callable=AsyncMock)
async def test_update_scan_source_callback(mock_save_source_result):
    scan_id = uuid4()
    db = AsyncMock()

    scan = SimpleNamespace(
        id = scan_id,
        status = SimpleNamespace(value="running"),
        progress = 37,
    )

    mock_save_source_result.return_value = scan

    payload = ScanCallbackRequest(
        status = "completed",
        raw_result = {"Raw Result of some kind": True},
        assets = [],
        findings = [],
        error_message = None,
    )

    result = await update_scan_source_callback(scan_id, "dns", payload, db)

    mock_save_source_result.assert_awaited_once_with(
        db = db,
        scan_id = scan_id,
        source_name = "dns",
        payload = payload.model_dump(),
    )

    assert result == {
        "scan_id": str(scan_id),
        "source_name": "dns",
        "scan_status": "running",
        "progress": 37,
    }