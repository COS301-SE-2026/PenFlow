#unit test for scan repo :db session is fully mocked
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.models.base import ScanStatus
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
    fake_scan = SimpleNamespace(
        id = uuid4(), 
        progress =0, 
        status= ScanStatus.RUNNING, 
        error_message=None,
        scan_type=SimpleNamespace(value="passive_ctem")
    )
    
    mock_get_scan.return_value =fake_scan

    source_result = MagicMock()
    source_result.scalar_one_or_none.return_value = None # no scan source

    asset_insert_result = MagicMock()
    asset_result = MagicMock()
    asset_result.scalar_one_or_none.return_value = SimpleNamespace(id=uuid4())

    status_result = MagicMock()
    status_result.all.return_value = [
        ("dns", ScanSourceStatus.COMPLETED),
    ]

    db.execute = AsyncMock(
        side_effect = [
            source_result,
            asset_insert_result,
            asset_result,
            status_result,
        ]
    )

    payload = {
        "status": "completed",
        "raw_result" :{"ok":True},
        "assets": [{"identifier":"sub.example.com","asset_type":"subdomain"}],
        "findings": [{"severity":"high","title": "Exposed panel"}]
    }

    scan = await ScanRepository.save_source_result(db,fake_scan.id,"dns",payload)

    assert scan.progress == 14
    assert scan.status == ScanStatus.RUNNING
    assert db.add.call_count == 1
    db.flush.assert_awaited_once()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(fake_scan)



#test update scan resource
@pytest.mark.asyncio
@patch("app.repositories.scan_repo.ScanRepository.get_scan_by_id",
new_callable = AsyncMock)
async def test_save_source_result_updates_existing_soruce(mock_get_scan):
    db = _make_db()
    fake_scan = SimpleNamespace(id = uuid4(), 
                                progress =0, 
                                status= ScanStatus.RUNNING,
                                scan_type=SimpleNamespace(value="passive_ctem")
    )
    mock_get_scan.return_value =fake_scan

    source_result = MagicMock()
    status_result = MagicMock()
    status_result.all.return_value = [
        ("shodan", ScanSourceStatus.FAILED),
    ]

    db.execute= AsyncMock(side_effect = [source_result,status_result])
    
    await ScanRepository.save_source_result(db,  fake_scan.id , "shodan",{"status":"failed"})

    assert db.execute.await_count == 2
    assert db.add.call_count == 0
    db.commit.assert_awaited_once()

#Test roll back
@pytest.mark.asyncio
@patch("app.repositories.scan_repo.ScanRepository.get_scan_by_id",
new_callable = AsyncMock)
async def test_save_source_result_roll_back_on_db_error(mock_get_scan):
    db =_make_db()
    fake_scan = SimpleNamespace(id = uuid4(),
                                progress =0, 
                                status= ScanStatus.RUNNING,
                                error_message=None,
                                scan_type=SimpleNamespace(value="passive_ctem")
    )
    mock_get_scan.return_value  =  fake_scan
    source_result = MagicMock()
    source_result.scalar_one_or_none.return_value = None # no scan source
    db.execute = AsyncMock(return_value = source_result)
    db.flush.side_effect = SQLAlchemyError("boom")

    with pytest.raises(SQLAlchemyError):
        await ScanRepository.save_source_result(db,fake_scan.id,"dns",{"status":"completed"})
    db.rollback.assert_awaited_once()

#Test list scan method  
@pytest.mark.asyncio
async def test_list_scans_maps_rows_to_dicts():
    db =_make_db()
    #change naming convention following sonar
    fake_scan = SimpleNamespace(id = uuid4() , 
    domain = "example.com",
    created_at = "2026-01-01",
    status= ScanStatus.COMPLETED,
    scan_type="passive_ctem",
    progress=100
    )

    row = SimpleNamespace(
        Scan =fake_scan,
        total_findings = 3,
        critical_count = 1,
        high_count =1,
        medium_count=1,
        low_count=0
    )
    result =MagicMock()
    result.all.return_value = [row]
    db.execute =AsyncMock(return_value =result)

    scans = await ScanRepository.list_scans(db,uuid4())

    assert scans == [{
        "id":fake_scan.id,
        "domain": "example.com",
        "created_at": "2026-01-01",
        "status": ScanStatus.COMPLETED,
        "scan_type": "passive_ctem",
        "progress": 100,
        "total_findings": 3,
        "critical_count": 1,
        "high_count": 1,
        "medium_count": 1,
        "low_count": 0,

    }]

#Test scan status when no scan return
@patch("app.repositories.scan_repo.ScanRepository.get_scan_by_id",new_callable =AsyncMock)
async def test_get_scan_status_returns_none_when_scan_missing(mock_get_scan):
    db = _make_db()
    mock_get_scan.return_value =None 
    result =await  ScanRepository.get_scan_status(db,uuid4(),
                                                  None)

    assert result is None