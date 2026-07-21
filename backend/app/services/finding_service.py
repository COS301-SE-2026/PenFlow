from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.base import Severity
from app.repositories.finding_repository import FindingRepository
from app.schemas.domain import SortOrder
from app.schemas.finding import \
(
    FindingCounts,
    FindingItem,
    FindingList,
    FindingPagination,
    FindingSortField,
)

#only need 1 service for now, to orchestrate
#service between html and sql
class FindingService:

    @staticmethod
    async def list_findings\
    (
        db: AsyncSession,
        scan_id: UUID,
        severity: Severity | None,
        search: str | None,
        sort: FindingSortField,
        order: SortOrder,
        limit: int,
        offset: int,
    ) -> FindingList:

        #retrieve the requested findings
        findings, total = await FindingRepository.list_findings\
        (
            db=db,
            scan_id=scan_id,
            severity=severity,
            search=search,
            sort=sort,
            order=order,
            limit=limit,
            offset=offset,
        )

        #Retrieve the counts for each seveverity
        counts = await FindingRepository.get_severity_counts\
        (
            db=db,
            scan_id=scan_id,
        )

        #pagination
        pagination = FindingPagination\
        (
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total,
        )

        #response the front end will use
        return FindingList\
        (
            items=\
            [
                FindingItem.model_validate(find)
                for find in findings
            ],
            counts=FindingCounts\
            (
                all=total,
                info=counts["info"],
                low=counts["low"],
                medium=counts["medium"],
                high=counts["high"],
                critical=counts["critical"],
            ),
            pagination=pagination,
        )