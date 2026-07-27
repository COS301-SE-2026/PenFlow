#intergrations  for scan repo run agaisnt real postgress session(db session fixutre)
from uuid import UUID

import pytest

from app.models.base import ScanStatus
from app.repositories.scan_repo import ScanRepository


@pytest.mark.asyncio
async def test_create_scan_success(db_session):
    domain = "example.com"
    email = "test@example.com"

    # execute 
    new_scan = await ScanRepository.create_scan(db_session,
                                                 domain=domain,
                                                 scan_type="passive_ctem",
                                                 email=email)

    assert new_scan.id is not None
    assert new_scan.domain == domain
    assert new_scan.email == email
    assert new_scan.status == ScanStatus.QUEUED
    assert new_scan.progress == 0

@pytest.mark.asyncio
async def test_get_scan_by_id_success(db_session):

    domain = "pen-flow.com"
    new_scan = await ScanRepository.create_scan(db_session, domain)

    retrieved_scan = await ScanRepository.get_scan_by_id(db_session, new_scan.id)

    assert retrieved_scan is not None
    assert retrieved_scan.id == new_scan.id
    assert retrieved_scan.domain == domain

@pytest.mark.asyncio
async def test_get_scan_by_id_not_found(db_session):
    random_id = UUID("00000000-0000-0000-0000-000000000000")
    retrieved_scan = await ScanRepository.get_scan_by_id(db_session, random_id)

    assert retrieved_scan is None

@pytest.mark.asyncio
async def test_mark_scan_failed(db_session):
    new_scan = await ScanRepository.create_scan(db_session, "fail-test.com")
    error_msg = "DNS resolution failed"

    failed_scan = await ScanRepository.mark_scan_failed(
        db=db_session,
        scan_id=new_scan.id,
        error_message=error_msg,
        is_partial=False
    )

    assert failed_scan.status == ScanStatus.FAILED
    assert failed_scan.error_message == error_msg