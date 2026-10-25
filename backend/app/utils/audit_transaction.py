from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, ParamSpec, TypeVar, cast

from sqlalchemy.ext.asyncio import AsyncSession

P = ParamSpec("P")
T = TypeVar("T")
_KEY = "penflow.audit_transaction"


@dataclass
class _Transaction:
    callbacks: list[Callable[[], Awaitable[Any]]] = field(default_factory=list)
    failed: bool = False


def _state(db: AsyncSession) -> _Transaction | None:
    value = db.info.get(_KEY)
    return value if isinstance(value, _Transaction) else None


async def commit_or_flush(db: AsyncSession) -> None:
    if _state(db) is None:
        await db.commit()
    else:
        await db.flush()


async def after_commit(
        db: AsyncSession,
        callback: Callable[[], Awaitable[Any]],
) -> None:
    state = _state(db)
    if state is None:
        await callback()
    else:
        state.callbacks.append(callback)


@asynccontextmanager
async def audit_transaction(db: AsyncSession) -> AsyncIterator[None]:
    existing = _state(db)

    if existing is not None:
        try:
            yield
        except BaseException:
            existing.failed = True
            raise
        return

    state = _Transaction()
    db.info[_KEY] = state

    try:
        yield

        if state.failed:
            raise RuntimeError("A nested audit operation failed")

        await db.commit()

    except BaseException:
        await db.rollback()
        raise

    finally:
        db.info.pop(_KEY, None)

    for callback in state.callbacks:
        await callback()


def audited_operation(
        function: Callable[P, Awaitable[T]],
) -> Callable[P, Awaitable[T]]:
    @wraps(function)
    async def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        db = cast(AsyncSession, args[0] if args else kwargs["db"])

        async with audit_transaction(db):
            return await function(*args, **kwargs)

    return wrapped