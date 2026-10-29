from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.base import EngagementStatus
from app.services.service_delivery_service import ServiceDeliveryService


@pytest.mark.asyncio
async def test_review_note_is_preserved_on_engagement_but_not_copied_to_audit(
    monkeypatch,
):
    engagement = SimpleNamespace(
        id=uuid4(),
        status=EngagementStatus.REVIEW,
        assigned_to=uuid4(),
        title="test",
    )

    update = AsyncMock(return_value=engagement)
    audit = AsyncMock()

    monkeypatch.setattr(
        ServiceDeliveryService,
        "require_owned_engagement",
        AsyncMock(return_value=engagement),
    )
    monkeypatch.setattr(
        ServiceDeliveryService,
        "action_response",
        lambda value: "ok",
    )
    monkeypatch.setattr(
        "app.services.service_delivery_service.EngagementRepository.update_fields",
        update,
    )
    monkeypatch.setattr(
        "app.services.service_delivery_service.AuditRepository.create_log",
        audit,
    )
    monkeypatch.setattr(
        "app.services.service_delivery_service.NotificationService.notify",
        AsyncMock(),
    )

    db = SimpleNamespace(
        info={},
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )

    await ServiceDeliveryService.return_from_review(
        db,
        engagement.id,
        uuid4(),
        SimpleNamespace(review_note="Keep this note"),
    )

    assert update.await_args.kwargs["changes"]["review_note"] == "Keep this note"
    assert "review_note" not in audit.await_args.kwargs["metadata"]

    db.commit.assert_awaited_once()