from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.utils.audit_transaction import (
    after_commit,
    audit_transaction,
    audited_operation,
    commit_or_flush,
)


def session():
    return SimpleNamespace(
        info={},
        commit=AsyncMock(),
        rollback=AsyncMock(),
        flush=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_repositories_keep_standalone_commit_behaviour():
    db = session()

    await commit_or_flush(db)

    db.commit.assert_awaited_once()
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_business_and_audit_commit_once():
    db = session()

    async with audit_transaction(db):
        await commit_or_flush(db)
        await commit_or_flush(db)
        db.commit.assert_not_awaited()

    db.commit.assert_awaited_once()
    assert db.flush.await_count == 2
    assert db.info == {}


@pytest.mark.asyncio
async def test_audit_failure_rolls_back_and_discards_dispatch():
    db = session()
    dispatch = AsyncMock()

    with pytest.raises(ValueError):
        async with audit_transaction(db):
            await commit_or_flush(db)
            await after_commit(db, dispatch)
            raise ValueError("audit insert failed")

    db.commit.assert_not_awaited()
    db.rollback.assert_awaited_once()
    dispatch.assert_not_awaited()
    assert db.info == {}


@pytest.mark.asyncio
async def test_commit_failure_does_not_dispatch():
    db = session()
    db.commit.side_effect = RuntimeError("database failed")
    dispatch = AsyncMock()

    with pytest.raises(RuntimeError):
        async with audit_transaction(db):
            await after_commit(db, dispatch)

    db.rollback.assert_awaited_once()
    dispatch.assert_not_awaited()
    assert db.info == {}


@pytest.mark.asyncio
async def test_dispatch_is_after_commit_and_outside_transaction():
    db = session()

    async def dispatch():
        db.commit.assert_awaited_once()
        assert db.info == {}

    async with audit_transaction(db):
        await after_commit(db, dispatch)


@pytest.mark.asyncio
async def test_dispatch_failure_does_not_attempt_database_rollback():
    db = session()
    dispatch = AsyncMock(side_effect=RuntimeError("broker unavailable"))

    with pytest.raises(RuntimeError):
        async with audit_transaction(db):
            await after_commit(db, dispatch)

    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_nested_operation_cannot_commit_early():
    db = session()

    async with audit_transaction(db):
        async with audit_transaction(db):
            await commit_or_flush(db)

        db.commit.assert_not_awaited()

    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_swallowed_nested_failure_still_prevents_commit():
    db = session()

    with pytest.raises(RuntimeError, match="nested audit"):
        async with audit_transaction(db):
            try:
                async with audit_transaction(db):
                    raise ValueError("nested failure")
            except ValueError:
                pass

    db.commit.assert_not_awaited()
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_standalone_dispatch_runs_immediately():
    db = session()
    dispatch = AsyncMock()

    await after_commit(db, dispatch)

    dispatch.assert_awaited_once()


@pytest.mark.asyncio
async def test_decorator_accepts_keyword_session_and_returns_result():
    db = session()

    @audited_operation
    async def operation(db, value):
        await commit_or_flush(db)
        return value

    assert await operation(db=db, value=42) == 42
    db.commit.assert_awaited_once()