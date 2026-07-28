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
    db.add = MagicMock() #mock for adding object to session
    db.commit = AsyncMock() #mock from committing transaction
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
    count_result = MagicMock()
    count_result.all.return_value = [("dns", ScanSourceStatus.COMPLETED)]
    db.execute = AsyncMock(side_effect = [source_result,count_result])

    payload = {
        "status": "completed",
        "raw_result" :{"ok":True},
        "assets": [{"identifier":"sub.example.com","asset_type":"subdomain"}],
        "findings": [{"severity":"high","title": "Exposed panel"}]
    }

    scan = await ScanRepository.save_source_result(db,fake_scan.id,"dns",payload)

    assert scan.progress == 14
    assert scan.status == ScanStatus.RUNNING
    assert db.add.call_count ==3 #scan source,asset ,finding too make the 3
    db.flush.assert_awaited_once()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(fake_scan)



#test update scan resource
@pytest.mark.asyncio
@patch("app.repositories.scan_repo.ScanRepository.get_scan_by_id",
new_callable = AsyncMock)
async def test_save_source_result_updates_existing_soruce(mock_get_scan):
    db = _make_db()
    fake_scan = SimpleNamespace(
        id = uuid4(),
        progress =0, 
        status= ScanStatus.RUNNING,
        scan_type=SimpleNamespace(value="passive_ctem")
    )
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

#test scan source when all the source succeed
#This test covers when all scan source is completely works 
@pytest.mark.asyncio
@patch("app.repositories.scan_repo.ScanRepository.get_scan_by_id",new_callable =AsyncMock)
async def test_save_source_result_marks_scan_completed_when_all_sources_succeed(mock_get_scan):
    db = _make_db()
    fake_scan = SimpleNamespace(
        id = uuid4(),
        progress =0, 
        status= ScanStatus.RUNNING,
        scan_type=SimpleNamespace(value="passive_ctem")
    )
    mock_get_scan.return_value =fake_scan

    #mock source result update query
    source_result = MagicMock()
    source_result.scalar_one_or_none.return_value = None # no scan source

    #mock status aggregation
    count_result = MagicMock()
    #passive osint scan workers
    count_result.all.return_value = [
        ("dns",ScanSourceStatus.COMPLETED),
        ("urlscan",ScanSourceStatus.COMPLETED),
        ("wappalyzer",ScanSourceStatus.COMPLETED),
        ("crt.sh",ScanSourceStatus.COMPLETED),
        ("shodan",ScanSourceStatus.COMPLETED),
        ("hunter.io",ScanSourceStatus.COMPLETED),
        ("hibp",ScanSourceStatus.COMPLETED),

    ]
    db.execute = AsyncMock(side_effect = [ source_result, count_result])

    #update source result (hibp)
    scan = await ScanRepository.save_source_result(db,fake_scan.id,"hibp",{"status":"completed"})

    #assert
    assert scan.status == ScanStatus.COMPLETED
    assert scan.progress == 100
    assert scan.error_message is None

#test error handling when scans roll back
@pytest.mark.asyncio
async def test_create_scan_roll_back_on_db_error():
    db = _make_db()
    db.commit = AsyncMock(side_effect = SQLAlchemyError("boom"))

    with pytest.raises(SQLAlchemyError):
        await ScanRepository.create_scan(db,domain= "example.com")

    db.rollback.assert_awaited_once()

#list scan status filter
@pytest.mark.asyncio
async def test_list_scans_filter_by_status():
    "test the list_scans properly filters scans by their status"
    db = _make_db()
    result = MagicMock()
    result.all.return_value = [] # simulate no scans found in a give status

    db.execute = AsyncMock(return_value = result)

    scans = await ScanRepository.list_scans(db,uuid4(),status=ScanStatus.COMPLETED)

    #verified empty list is return when no scans match the status
    assert scans == []
    #
    db.execute.assert_awaited_once()
    
       