from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.repositories.engagement_repository import (
    EngagementRepository,
)
from app.schemas.engagement import (
    EngagementSortField,
    SortOrder,
)
from app.services.engagement_service import (
    EngagementService,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "relationship"),
    [
        ("client", "requested_by"),
        ("pentester", "assigned_to"),
        ("service_delivery", None),
    ],
)
async def test_engagement_detail_authorization_by_role(
    monkeypatch: pytest.MonkeyPatch,
    role: str,
    relationship: str | None,
) -> None:
    user_id = uuid4()
    unrelated_id = uuid4()

    engagement = SimpleNamespace(
        requested_by=unrelated_id,
        assigned_to=unrelated_id,
        service_delivery_id=unrelated_id,
    )

    if relationship is not None:
        setattr(
            engagement,
            relationship,
            user_id,
        )

    monkeypatch.setattr(
        EngagementRepository,
        "get_by_id",
        AsyncMock(return_value=engagement),
    )
    monkeypatch.setattr(
        EngagementRepository,
        "get_user_by_id",
        AsyncMock(
            return_value=SimpleNamespace(
                id=user_id,
                role=role,
            )
        ),
    )

    result = (
        await EngagementService
        .require_viewable_engagement(
            AsyncMock(),
            engagement_id=uuid4(),
            user_id=user_id,
        )
    )

    assert result is engagement


@pytest.mark.asyncio
async def test_unrelated_client_cannot_view_engagement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid4()
    unrelated_id = uuid4()

    monkeypatch.setattr(
        EngagementRepository,
        "get_by_id",
        AsyncMock(
            return_value=SimpleNamespace(
                requested_by=unrelated_id,
                assigned_to=unrelated_id,
                service_delivery_id=unrelated_id,
            )
        ),
    )
    monkeypatch.setattr(
        EngagementRepository,
        "get_user_by_id",
        AsyncMock(
            return_value=SimpleNamespace(
                id=user_id,
                role="client",
            )
        ),
    )

    with pytest.raises(HTTPException) as error:
        await (
            EngagementService
            .require_viewable_engagement(
                AsyncMock(),
                engagement_id=uuid4(),
                user_id=user_id,
            )
        )

    assert error.value.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "expected_column"),
    [
        ("client", "engagements.requested_by"),
        ("pentester", "engagements.assigned_to"),
        ("service_delivery", None),
    ],
)
async def test_engagement_list_scope_by_role(
    role: str,
    expected_column: str | None,
) -> None:
    db = AsyncMock()

    result = MagicMock()
    result.all.return_value = []

    db.execute = AsyncMock(return_value=result)
    db.scalar = AsyncMock(return_value=0)

    await EngagementRepository.list_assigned(
        db,
        user_id=uuid4(),
        user_role=role,
        engagement_status=None,
        search=None,
        sort=EngagementSortField.UPDATED_AT,
        order=SortOrder.DESC,
        limit=10,
        offset=0,
    )

    statement = db.execute.await_args.args[0]
    where_clause = statement.whereclause

    if expected_column is None:
        assert where_clause is None

    else:
        assert where_clause is not None
        assert expected_column in str(where_clause)