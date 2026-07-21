from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.models.finding import Finding
from app.models.base import Severity
from app.schemas.finding import FindingSortField, SortOrder


class FindingRepository:


    @staticmethod
    def sort_records\
    (
        query: Select[Any],
        sort: FindingSortField,
        order: SortOrder,
    ) -> Select[Any]:

        #like sort_cols from domain_repo
        sort_cols: dict[FindingSortField, InstrumentedAttribute[Any]] = \
        {
            FindingSortField.SEVERITY: Finding.severity,
            FindingSortField.TITLE: Finding.title,
            FindingSortField.CREATED_AT: Finding.created_at,
        }

        sort_col = sort_cols[sort]

        if order == SortOrder.ASC:
            return query.order_by\
            (
                sort_col.asc(),
                Finding.id.asc(),
            )

        return query.order_by\
        (
            sort_col.desc(),
            Finding.id.desc(),
        )

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
    ) -> tuple[list[Finding], int]:

        query = select(Finding).where\
        (
            Finding.scan_id == scan_id,
        )

        count_query = select(func.count(Finding.id)).where\
        (
            Finding.scan_id == scan_id,
        )

        if severity is not None:
            query = query.where\
            (
                Finding.severity == severity,
            )

            count_query = count_query.where\
            (
                Finding.severity == severity,
            )

        stripped_search = search.strip() if search else None

        #search ability
        if stripped_search:
            finding_filter = \
            (
                Finding.title.ilike(f"%{stripped_search}%")
                | Finding.description.ilike(f"%{stripped_search}%")
            )

            query = query.where(finding_filter)
            count_query = count_query.where(finding_filter)

        query = FindingRepository.sort_records\
        (
            query,
            sort=sort,
            order=order,
        )

        query = query.limit(limit).offset(offset)

        result = await db.execute(query)
        findings = list(result.scalars().all())

        total = int(await db.scalar(count_query) or 0)

        return findings, total

    @staticmethod
    async def get_severity_counts\
    (
        db: AsyncSession,
        scan_id: UUID,
    ) -> dict[Severity, int]:

        query = \
        (
            select(
                Finding.severity,
                func.count(Finding.id),
            )
            .where(Finding.scan_id == scan_id)
            .group_by(Finding.severity)
        )

        result = await db.execute(query)

        counts = \
        {
            Severity.INFO: 0,
            Severity.LOW: 0,
            Severity.MEDIUM: 0,
            Severity.HIGH: 0,
            Severity.CRITICAL: 0,
        }

        for severity, count in result.all():
            counts[severity] = int(count)

        return counts