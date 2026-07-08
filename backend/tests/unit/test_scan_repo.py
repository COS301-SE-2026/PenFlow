import pytest
from uuid import UUID
from app.repositories.scan_repo import ScanRepository
from app.models.base import ScanStatus
from app.models.scan import Scan

@pytest.mark.asyncio
async def test_create_scan_success(db_session):
    domain = "example.com"
    email = "test@example.com"

    # execute 
    new_scan = await ScanRepository.create_scan(db_session, domain, email)

    assert new_scan.id is not None
    assert new_scan.domain == domain
    assert new_scan.email == email
    assert new_scan.status == ScanStatus.QUEUED
    assert new_scan.progress == 0

@pytest.mark.asyncio
async def test_get_scan_by_id_success(db_session):

    domain = "pen-flow.com"
    new_scan = await ScanRepository.create_scan(db_session, domain)

    assert retrieed_scan is not None
    assert retrieved_scan.id == new_scan.id
    assert retrieved_scan.domain == domain