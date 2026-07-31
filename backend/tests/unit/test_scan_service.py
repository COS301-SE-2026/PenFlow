from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.scan import InitiateScanRequest, ScanTypeEnum
from app.services.scan_service import ScanService


def _scan_data(**overrides):
    defaults ={
        "domain": "example.com",
        "scan_type": ScanTypeEnum.PASSIVE_CTEM,
        "verified_domain_id": None,
        "email": None
    }
    defaults.update(overrides)
    return InitiateScanRequest(**defaults)


#happy path for passive ctem scan
@pytest.mark.asyncio
@patch("app.services.scan_service.celery_app.send_task")
@patch("app.services.scan_service.ScanRepository.create_scan",new_callable=AsyncMock)
async def test_start_scan_passive_queues_full_task(mock_create_scan,mock_send_task):
        db =AsyncMock()
        scan_record = SimpleNamespace(id=uuid4())
        mock_create_scan.return_value = scan_record

        scan_data = _scan_data()

        result = await ScanService.start_scan(db,scan_data)

        assert result is scan_record
        mock_create_scan.assert_awaited_once_with(
              db=db,
              domain = "example.com",
              scan_type = ScanTypeEnum.PASSIVE_CTEM.value ,
              email = None,
              user_id = None,
              verified_domain_id = None,
        )
        mock_send_task.assert_called_once_with(
              "scan.full",args=[str(scan_record.id),"example.com"]
        )


#  test when 400 occurs 
@pytest.mark.asyncio
async def  test_start_scan_active_without_verified_domain_id_raises():
    db =AsyncMock
    scan_data = _scan_data(scan_type = ScanTypeEnum.ACTIVE_VULNERABILITY)

    with pytest.raises(HTTPException) as exe_info:
            await ScanService.start_scan(db,scan_data, user_id= uuid4())

    assert exe_info.value.status_code ==400
    assert "verified_domain_id is required" in exe_info.value.detail

#  test when 401 occurs
@pytest.mark.asyncio
async def  test_start_scan_active_without_user_id_raises(): 
        db =AsyncMock()
        scan_data = _scan_data(
            scan_type = ScanTypeEnum.ACTIVE_VULNERABILITY,
            verified_domain_id =uuid4(),
            )
        with pytest.raises(HTTPException) as exc_info:
                await ScanService.start_scan(db,scan_data,user_id= None)

        assert exc_info.value.status_code ==401
        assert "Authentication required " in exc_info.value.detail

# domain lookup returns none
@pytest.mark.asyncio
@patch("app.services.scan_service.DomainRepository.get_by_id",new_callable=AsyncMock)
async def  test_start_scan_active_domain_not_found_raises_403(mock_get_by_id): 
        db =AsyncMock()
        mock_get_by_id.return_value = None

        scan_data = _scan_data(
            scan_type = ScanTypeEnum.ACTIVE_VULNERABILITY,
            verified_domain_id =uuid4(),
            )
        with pytest.raises(HTTPException) as exc_info:
                await ScanService.start_scan(db,scan_data,user_id= uuid4())

        assert exc_info.value.status_code ==403
        assert "fully verified domain" in exc_info.value.detail

#test status is pending not verified
@pytest.mark.asyncio
@patch("app.services.scan_service.DomainRepository.get_by_id",new_callable=AsyncMock)
async def  test_start_scan_active_domain_not_verified_raises_403(mock_get_by_id): 
        db =AsyncMock()
        mock_get_by_id.return_value = SimpleNamespace(
               status = SimpleNamespace(value ="pending"),
               domain = "example.com",
        )

        scan_data = _scan_data(
            scan_type = ScanTypeEnum.ACTIVE_VULNERABILITY,
            verified_domain_id =uuid4(),
            )
        with pytest.raises(HTTPException) as exc_info:
                await ScanService.start_scan(db,scan_data,user_id= uuid4())

        assert exc_info.value.status_code ==403
        assert "fully verified domain" in exc_info.value.detail

#test status is pending not verified
@pytest.mark.asyncio
@patch("app.services.scan_service.DomainRepository.get_by_id",new_callable=AsyncMock)
async def  test_start_scan_active_domain_mismatch_raises_400(mock_get_by_id): 
        db =AsyncMock()
        mock_get_by_id.return_value = SimpleNamespace(
               status = SimpleNamespace(value ="verified"),
               domain = "other.com",
        )

        scan_data = _scan_data(
            domain = "example.com",
            scan_type = ScanTypeEnum.ACTIVE_VULNERABILITY,
            verified_domain_id =uuid4(),
            )
        with pytest.raises(HTTPException) as exc_info:
                await ScanService.start_scan(db,scan_data,user_id= uuid4())

        assert exc_info.value.status_code ==400
        assert "does not match" in exc_info.value.detail

#happy path for phase 2 scan
@pytest.mark.asyncio 
@patch("app.services.scan_service.celery_app.send_task")
@patch("app.services.scan_service.ScanRepository.create_scan",new_callable=AsyncMock)
@patch("app.services.scan_service.DomainRepository.get_by_id",new_callable=AsyncMock)
async def test_start_scan_active_happy_path_queues_phase2_task(
  mock_get_by_id, mock_create_scan ,mock_send_task     
):
    db = AsyncMock()
    user_id = uuid4()
    verified_domain_id = uuid4()
    scan_record = SimpleNamespace(id = uuid4())

    mock_get_by_id.return_value = SimpleNamespace(
            status = SimpleNamespace(value ="verified"),
            domain = "Example.com",
            )
    mock_create_scan.return_value = scan_record
    scan_data = _scan_data(
               domain = "example.com",
               scan_type = ScanTypeEnum.ACTIVE_VULNERABILITY,
               verified_domain_id = verified_domain_id,
        )
    result = await ScanService.start_scan(db,scan_data,user_id= user_id)

    assert result is scan_record
    mock_create_scan.assert_awaited_once_with(
           db=db,
           domain= "example.com",
           scan_type = ScanTypeEnum.ACTIVE_VULNERABILITY.value,
           email = None,
           user_id = user_id,
           verified_domain_id = verified_domain_id,
    )
    mock_send_task.assert_called_once_with(
           "scan.phase2_full",args = [str(scan_record.id),"example.com"]
    )
  