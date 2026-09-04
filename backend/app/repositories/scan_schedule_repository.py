from datetime import datetime, time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import ScanScheduleFrequency, ScanStatus, ScanType
from app.models.scan import Scan
from app.models.scan_schedule import ScanSchedule


class ScanScheduleRepository:

    @staticmethod
    async def create_schedule(
        db: AsyncSession,
        *,
        user_id: UUID,
        verified_domain_id: UUID,
        scan_type: ScanType,
        frequency: ScanScheduleFrequency,
        run_time: time,
        day_of_week: int | None,
        day_of_month: int | None,
        timezone_name: str,
        next_run_at: datetime,
    ) -> ScanSchedule:
        schedule = ScanSchedule(
            user_id=user_id,
            verified_domain_id=verified_domain_id,
            scan_type=scan_type,
            frequency=frequency,
            run_time=run_time,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
            timezone=timezone_name,
            next_run_at=next_run_at,
            is_active=True,
        )

        db.add(schedule)
        await db.flush()

        return schedule


    @staticmethod
    async def list_for_user(
        db: AsyncSession,
        user_id: UUID,
    ) -> list[ScanSchedule]:
        result = await db.execute(
            select(ScanSchedule).where(
                ScanSchedule.user_id == user_id,
            ).order_by(
                ScanSchedule.is_active.desc(),
                ScanSchedule.next_run_at.asc(),
                ScanSchedule.id.asc(),
            )
        )

        return list(result.scalars().all())


    @staticmethod
    async def get_for_user(
        db: AsyncSession,
        schedule_id: UUID,
        user_id: UUID,
    ) -> ScanSchedule | None:
        result = await db.execute(
            select(ScanSchedule).where(
                ScanSchedule.id == schedule_id,
                ScanSchedule.user_id == user_id,
            )
        )

        return result.scalar_one_or_none()


    @staticmethod
    async def get_next_due(
        db: AsyncSession,
        due_at: datetime,
    ) -> ScanSchedule | None:
        result = await db.execute(
            select(ScanSchedule).options(
                selectinload(ScanSchedule.verified_domain),
            ).where(
                ScanSchedule.is_active.is_(True),
                ScanSchedule.next_run_at <= due_at,
            ).order_by(
                ScanSchedule.next_run_at.asc(),
                ScanSchedule.id.asc(),
            ).limit(1).with_for_update(
                of=ScanSchedule,
                skip_locked=True,
            )
        )

        return result.scalar_one_or_none()


    @staticmethod
    async def get_or_create_occurrence(
        db: AsyncSession,
        schedule: ScanSchedule,
        scheduled_for: datetime,
    ) -> Scan:
        stmt = (
            insert(Scan).values(
                user_id=schedule.user_id,
                verified_domain_id=schedule.verified_domain_id,
                schedule_id=schedule.id,
                scheduled_for=scheduled_for,
                domain=schedule.verified_domain.domain,
                scan_type=schedule.scan_type,
                status=ScanStatus.QUEUED,
                progress=0,
            ).on_conflict_do_nothing(
                constraint="uq_scans_schedule_occurrence",
            ).returning(Scan.id)
        )

        scan_id = (await db.execute(stmt)).scalar_one_or_none()

        if scan_id is None:
            scan_id = await db.scalar(
                select(Scan.id).where(
                    Scan.schedule_id == schedule.id,
                    Scan.scheduled_for == scheduled_for,
                )
            )

        if scan_id is None:
            raise RuntimeError("Failed to create or retrieve scheduled scan")

        result = await db.execute(
            select(Scan).where(
                Scan.id == scan_id,
                Scan.schedule_id == schedule.id,
            ).with_for_update()
        )

        scan = result.scalar_one_or_none()

        if scan is None:
            raise RuntimeError("Scheduled scan occurence dissapeared")

        return scan


    @staticmethod
    async def delete_schedule(
        db: AsyncSession,
        schedule: ScanSchedule,
    ) -> None:
        await db.delete(schedule)


        