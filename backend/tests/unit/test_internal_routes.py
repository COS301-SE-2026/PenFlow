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
from app.models.base import ReportStatus, ScanStatus, ScanType
from app.schemas.report import ReportCallbackRequest
from app.schemas.scan import ScanCallbackRequest, ScanSourceCallbackRequest


@pytest.mark.asyncio
@patch("app.api.routes.internal.celery_app.send_task")
@patch("app.api.routes.internal.queue_report_generation", new_callable=AsyncMock)
@patch("app.api.routes.internal.ScanRepository.get_scan_by_id", new_callable=AsyncMock)
async def test_update_scan_status_completed_queues_report(
    mock_scan, 
    mock_queue_report, 
    mock_send_task
):
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
    mock_send_task.assert_called_once_with(
        "rag.index_scan",
        args=[str(scan_id)],
        queue="indexing",
        routing_key="indexing",
    )

    assert result == {
        "scan_id": str(scan_id),
        "status": "completed",
        "report_status": "generating",
    }


@pytest.mark.asyncio
@patch("app.api.routes.internal.celery_app.send_task")
@patch("app.api.routes.internal.queue_report_generation", new_callable=AsyncMock)
@patch("app.api.routes.internal.ScanRepository.get_scan_by_id", new_callable=AsyncMock)
async def test_update_scan_status_running_does_not_queue_report(
    mock_scan, 
    mock_queue_report, 
    mock_send_task
):
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
    mock_send_task.assert_not_called()

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
async def test_update_report_status_completed(report_record):
    report, path = report_record
    db = AsyncMock()

    result = await update_report_status_callback(
        report.scan_id,
        ReportCallbackRequest(
            status="completed",
            pdf_path=str(path),
        ),
        db,
    )

    assert report.status == ReportStatus.COMPLETED
    assert report.pdf_path == str(path.resolve())
    db.commit.assert_awaited_once()

    assert result == {
        "scan_id": str(report.scan_id),
        "report_status": "completed",
    }


@pytest.mark.asyncio
async def test_update_report_status_failed(report_record):
    report, _ = report_record
    db = AsyncMock()

    result = await update_report_status_callback(
        report.scan_id,
        ReportCallbackRequest(
            status="failed",
            error_message="Report generation failed",
        ),
        db,
    )

    assert report.status == ReportStatus.FAILED
    assert report.error_message == "Report generation failed"
    db.commit.assert_awaited_once()

    assert result == {
        "scan_id": str(report.scan_id),
        "report_status": "failed",
    }


@pytest.mark.asyncio
async def test_update_report_status_completed_needs_pdfs_path(
    report_record,
):
    report, _ = report_record
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await update_report_status_callback(
            report.scan_id,
            ReportCallbackRequest(status="completed"),
            db,
        )

    assert exc.value.status_code == 422
    assert exc.value.detail == "pdf_path is required"
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_report_status_invalid(report_record):
    report, _ = report_record
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await update_report_status_callback(
            report.scan_id,
            ReportCallbackRequest(status="Incorrect Status"),
            db,
        )

    assert exc.value.status_code == 422
    assert exc.value.detail == "Invalid report callback status"
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
@patch("app.api.routes.internal.celery_app.send_task")
@patch("app.api.routes.internal.ScanRepository.save_source_result", new_callable=AsyncMock)
async def test_update_scan_source_callback(
    mock_save_source_result,
    mock_send_task,
    source_lookup,
):
    scan_id = uuid4()
    db = AsyncMock()

    scan = SimpleNamespace(
        id = scan_id,
        status = SimpleNamespace(value="running"),
        progress = 37,
    )

    mock_save_source_result.return_value = scan

    payload = ScanSourceCallbackRequest(
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
    mock_send_task.assert_not_called()

    assert result == {
        "scan_id": str(scan_id),
        "source_name": "dns",
        "scan_status": "running",
        "progress": 37,
        "report_status": None,
    }


@pytest.mark.asyncio
@patch("app.api.routes.internal.ScanRepository.save_source_result", new_callable=AsyncMock)
async def test_update_scan_source_callback_scan_not_found(mock_save_source_result, source_lookup):
    scan_id = uuid4()
    db = AsyncMock()
    source_lookup.return_value = None

    payload = ScanSourceCallbackRequest(
        status = "failed",
        raw_result = None,
        assets = [],
        findings = [],
        error_message = "Unable to retrieve DNS information",
    )

    with pytest.raises(HTTPException) as excep:
        await update_scan_source_callback(scan_id, "dns", payload, db)

    assert excep.value.status_code == 404
    assert excep.value.detail == "Scan not found"
    mock_save_source_result.assert_not_awaited()


@pytest.mark.asyncio
@patch("app.api.routes.internal.celery_app.send_task")
@patch("app.api.routes.internal.queue_report_generation", new_callable=AsyncMock)
@patch("app.api.routes.internal.get_report_by_scan_id", new_callable=AsyncMock)
@patch("app.api.routes.internal.ScanRepository.save_source_result", new_callable=AsyncMock)
async def test_completed_source_callback_queues_indexing(
    mock_save_source_result,
    mock_get_report,
    mock_queue_report,
    mock_send_task,
    source_lookup,
):
    scan_id = uuid4()
    db = AsyncMock()

    mock_save_source_result.return_value = (
        SimpleNamespace(
            id=scan_id,
            status=ScanStatus.COMPLETED,
            progress=100,
        )
    )
    mock_get_report.return_value = None
    mock_queue_report.return_value = {
        "status": "generating",
    }

    payload = ScanSourceCallbackRequest(
        status="completed",
        raw_result={},
        assets=[],
        services=[],
        technologies=[],
        findings=[],
        error_message=None,
    )

    result = await update_scan_source_callback(
        scan_id,
        "dns",
        payload,
        db,
    )

    mock_send_task.assert_called_once_with(
        "rag.index_scan",
        args=[str(scan_id)],
        queue="indexing",
        routing_key="indexing",
    )

    assert result == {
        "scan_id": str(scan_id),
        "source_name": "dns",
        "scan_status": "completed",
        "progress": 100,
        "report_status": "generating",
    }


@pytest.fixture
def report_record(monkeypatch, tmp_path):
    report = SimpleNamespace(
        scan_id=uuid4(),
        engagement_id=None,
        version=1,
        status=ReportStatus.GENERATING,
        pdf_path=None,
        generated_at=None,
        error_message=None,
    )

    monkeypatch.setattr(
        "app.api.routes.internal.get_report_by_scan_id",
        AsyncMock(return_value=report),
    )
    monkeypatch.setattr(
        "app.services.callback_validation.REPORT_STORAGE",
        "local",
    )
    monkeypatch.setattr(
        "app.services.callback_validation.REPORT_OUTPUT_DIR",
        tmp_path,
    )

    path = tmp_path / f"penflow_report_{report.scan_id}.pdf"
    return report, path


@pytest.fixture
def source_lookup(monkeypatch):
    lookup = AsyncMock(
        return_value=SimpleNamespace(
            scan_type=ScanType.PASSIVE_CTEM,
        )
    )

    monkeypatch.setattr(
        "app.api.routes.internal.ScanRepository.get_scan_by_id",
        lookup,
    )

    return lookup