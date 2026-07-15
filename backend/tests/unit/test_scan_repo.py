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


# test get scan by id
@pytest.mark.asyncio
async def test_get_scan_by_id_returns_scan():
    db = _make_db()
    fake_scan = SimpleNamespace(id = uuid4())
    result =MagicMock()
    result.scalar_one_or_none.return_value =fake_scan
    db.execute = AsyncMock(return_value = result)

    scan = await ScanRepository.get_scan_by_id(db,fake_scan.id)

    assert scan is fake_scan

# test result when scan is missing
@pytest.mark.asyncio
@patch("app.repositories.scan_repo.ScanRepository.get_scan_by_id",new_callable =AsyncMock)
async def test_save_source_result_raises_when_scan_missing(mock_get_scan):
    db = _make_db()
    mock_get_scan.return_value = None

    with pytest.raises(ValueError,match = "not found"):
        await ScanRepository.save_source_result(db,uuid4(),"dns",{"status":"completed"})

#test save_source resource create a new scansource when it doesn't exist
#test transition from running to  completed
#update scan source ,asset ,finding
# error handling when roll back

@pytest.mark.asyncio
@patch("app.repositories.scan_repo.ScanRepository.get_scan_by_id",
new_callable = AsyncMock)
async def test_save_source_result_creates_new_source_with_assets_and_findings(mock_get_scan):
    db = _make_db()
    fake_scan = SimpleNamespace(id = uuid4() , progress =0, status= ScanStatus.RUNNING)
    mock_get_scan.return_value =fake_scan

    source_result = MagicMock()
    source_result.scalar_one_or_none.return_value = None # no scan source
    count_result = MagicMock()
    count_result.scalar.return_value = len(
        __import__("app.repositories.scan_repo",fromlist =["TOTAL_SCAN_SOURCES"] ).TOTAL_SCAN_SOURCES
    )
    db.execute = AsyncMock(side_effect = [source_result,count_result])

    payload = {
        "status": "completed",
        "raw_result" :{"ok":True},
        "assets": [{"identifier":"sub.example.com","asset_type":"subdomain"}],
        "findings": [{"severity":"high","title": "Exposed panel"}]
    }

    scan = await ScanRepository.save_source_result(db,fake_scan.id,"dns",payload)

    assert scan.progress ==100
    assert scan.status == ScanStatus.COMPLETED
    assert db.add.call_count ==3 #scan source,asset ,finding too make the 3
    db.commit.assert_awaited_once()



#test update scan resource
@pytest.mark.asyncio
@patch("app.repositories.scan_repo.ScanRepository.get_scan_by_id",
new_callable = AsyncMock)
async def test_save_source_result_updates_existing_soruce(mock_get_scan):
    db = _make_db()
    fake_scan = SimpleNamespace(id = uuid4() , progress =0, status= ScanStatus.RUNNING)
    mock_get_scan.return_value =fake_scan

    existing_source =SimpleNamespace(status=None,raw_result=None,error_message=None)
    source_result = MagicMock()
    source_result.scalar_one_or_none.return_value = existing_source
    count_result = MagicMock()
    count_result.scalar.return_value =1
    db.execute= AsyncMock(side_effect = [source_result,count_result])
    
    await ScanRepository.save_source_result(db,  fake_scan.id , "shodan",{"status":"failed"})


    assert existing_source.status == ScanSourceStatus.FAILED 
    db.add.assert_not_called()
