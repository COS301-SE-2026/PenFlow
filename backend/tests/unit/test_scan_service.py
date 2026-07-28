from types import SimpleNamespace
from unittest.mock import AsyncMock , patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.scan import InitiateScanRequest, ScanTypeEnum
from app.services.scan_service import  ScanService

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
        