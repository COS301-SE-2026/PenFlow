from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import pytest
from app.models.brand_intelligence import BrandCandidateStatus
from app.repositories.brand_intelligence_repository import BrandIntelligenceRepository


@pytest.mark.asyncio
async def test_get_monitor():
    db = AsyncMock()
    monitor = SimpleNamespace(id=uuid4())
    result = MagicMock()
    result.scalar_one_or_none.return_value = monitor
    db.execute.return_value = result
    repo = BrandIntelligenceRepository(db)
    found = await (repo.get_monitoring_by_domain_id
    (
        uuid4()
    ))
    assert found is monitor


@pytest.mark.asyncio
async def test_create_monitor():
    db = AsyncMock()
    domain_id = uuid4()
    repo = BrandIntelligenceRepository(db)
    repo.get_monitoring_by_domain_id = (
    AsyncMock
    (
        side_effect=
        [
            None,
            SimpleNamespace
            (
                verified_domain_id=domain_id,
                is_active=True,
            ),
        ]
    ))
    result = await repo.create_or_activate_monitoring(domain_id)
    assert result.is_active is True
    db.add.assert_called_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_activate_monitor():
    db = AsyncMock()
    monitor = (SimpleNamespace
    (
        is_active=False
    ))
    repo = BrandIntelligenceRepository(db)
    repo.get_monitoring_by_domain_id = (AsyncMock
    (
        side_effect=[monitor,monitor]
    ))
    result = await repo.create_or_activate_monitoring(uuid4())
    assert result.is_active is True
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_candidate_missing():
    db = AsyncMock()
    db.get.return_value = None
    repo = BrandIntelligenceRepository(db)
    result = await (repo.update_candidate_status
    (
        uuid4(),
        BrandCandidateStatus.RESOLVED,
    ))
    assert result is None


@pytest.mark.asyncio
async def test_candidate_resolved():
    db = AsyncMock()
    candidate = (SimpleNamespace
    (
        status=BrandCandidateStatus.NEW,
        resolved_at=None,
    ))
    db.get.return_value = candidate
    repo = BrandIntelligenceRepository(db)
    result = await (repo.update_candidate_status
    (
        uuid4(),
        BrandCandidateStatus.RESOLVED,
    ))
    assert result.status == BrandCandidateStatus.RESOLVED
    assert result.resolved_at is not None