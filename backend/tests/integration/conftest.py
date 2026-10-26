from uuid import UUID

import pytest_asyncio

from app.api.dependencies.scan_access import issue_guest_token
from app.models.base import ScanStatus, ScanType
from app.models.scan import Scan


@pytest_asyncio.fixture
async def guest_scan_headers(db_session):
    async def grant(
        scan_id: UUID | str,
        *,
        domain: str = "guest-test.example",
    ) -> dict[str, str]:
        identifier = UUID(str(scan_id))
        scan = await db_session.get(Scan, identifier)

        if scan is None:
            scan = Scan(
                id=identifier,
                domain=domain,
                user_id=None,
                scan_type=ScanType.PASSIVE_CTEM,
                status=ScanStatus.COMPLETED,
                progress=100,
            )
            db_session.add(scan)
            await db_session.flush()

        assert scan.user_id is None
        assert scan.scan_type == ScanType.PASSIVE_CTEM

        return {
            "X-Scan-Token": issue_guest_token(identifier),
        }

    return grant