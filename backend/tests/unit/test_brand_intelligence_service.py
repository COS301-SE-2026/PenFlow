from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4
import pytest
from app.models.brand_intelligence import BrandCandidateStatus
from app.services.brand_intelligence_service import BrandIntelligenceService


@pytest.mark.asyncio
@patch("app.services.brand_intelligence_service.celery_app.send_task")
async def test_trigger_brand(mock_send_task):
    db = AsyncMock()
    user_id = uuid4()
    domain_id = uuid4()
    monitor_id = uuid4()
    db.get.return_value = (SimpleNamespace
    (
        status="verified",
        user_id=user_id,
        domain="jerry.com",
    ))

    service = BrandIntelligenceService(db)
    service.repo.create_or_activate_monitoring = (AsyncMock
    (
        return_value=SimpleNamespace(id=monitor_id)
    ))
    result = await (service.trigger_monitoring_run
    (
        domain_id,
        str(user_id),
    ))
    assert result.id == monitor_id
    (mock_send_task.assert_called_once_with
    (
        "brand.monitor_domain",
        args=[str(monitor_id),"jerry.com"],
    ))


@pytest.mark.asyncio
async def test_trigger_missing():
    db = AsyncMock()
    db.get.return_value = None
    service = BrandIntelligenceService(db)
    with (pytest.raises(ValueError)):
        await service.trigger_monitoring_run(
            uuid4(),
            str(uuid4()),
        )


@pytest.mark.asyncio
async def test_ingest_brand():
    db = AsyncMock()
    monitor_id = uuid4()
    db.get.return_value = (SimpleNamespace
    (
        id=monitor_id,
        is_active=True,
    ))

    service = BrandIntelligenceService(db)
    service.repo.upsert_candidates = AsyncMock()
    service.repo.update_run_timestamp = AsyncMock()
    payload = (SimpleNamespace
    (
        brand_monitoring_id=monitor_id,
        candidates=[],
    ))

    await service.ingest_worker_results(payload)
    service.repo.upsert_candidates.assert_awaited_once()
    service.repo.update_run_timestamp.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_brand():
    db = AsyncMock()
    candidate_id = uuid4()
    monitor_id = uuid4()
    domain_id = uuid4()
    user_id = uuid4()

    candidate = (SimpleNamespace
    (
        brand_monitoring_id=monitor_id
    ))

    monitor = (SimpleNamespace
    (
        verified_domain_id=domain_id
    ))

    domain = (SimpleNamespace
    (
        user_id=user_id
    ))

    db.get.side_effect =\
    [
        candidate,
        monitor,
        domain,
    ]

    service = BrandIntelligenceService(db)
    service.repo.update_candidate_status = (AsyncMock
    (
        return_value=candidate
    ))

    result = await (service.update_status
    (
        candidate_id,
        BrandCandidateStatus.RESOLVED,
        str(user_id),
    ))

    assert result is candidate