from types import SimpleNamespace
from unittest.mock import AsyncMock,MagicMock,patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.models.base import ScanStatus, Severity
from app.models.scan_source import ScanSourceStatus
from app.repositories.scan_repo import ScanRepository


# create a mock db with common method
def _make_db():
    db = MagicMock()
    db.add = MagicMock() #mock for adding objec to session
    db.commit = AsyncMock() #mock from commiting transcation
    db.rollback = AsyncMock() # mock for roll back
    db.refresh = AsyncMock() # mock for refreshing object
    db.flush = AsyncMock()  # mock for flushing session
    return db

#test create scan
#test scan create success with the given domain and email
@pytest.mark.asyncio
async def test_create_scan_success():

    db = _make_db()
    scan = await ScanRepository.create_scan(
    db,
    domain="example.com",
    email = "a@b.com"
    )

#assert 
    assert scan.domain == "example.com"
    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once()


# test get scan id
@pytest.mark.asyncio
async def test_get_scan_by_id_returns_scan():
    db = _make_db()
    fake_scan = SimpleNamespace(id = uuid4())
    result =MagicMock()
    result.scalar_one_or_none.return_value =fake_scan
    db.execute = AsyncMock(return_value = result)

    scan = await ScanRepository.get_scan_by_id(db,fake_scan.id)

    assert scan is fake_scan