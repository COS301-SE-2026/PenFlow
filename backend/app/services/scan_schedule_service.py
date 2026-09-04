import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import DomainVerificationStatus, ScanScheduleFrequency
from app.models.scan_schedule import ScanSchedule
from app.repositories.domain_repository import DomainRepository
from app.repositories.scan_schedule_repository import ScanScheduleRepository
from app.schemas.scan_schedule import ScanScheduleCreate, ScanScheduleUpdate
from app.services.scan_service import ScanService
from app.services.schedule_calculator import (
    ScheduleValidationError,
    calculate_next_run,
    validate_schedule,
)

logger = logging.getLogger(__name__)

RECURRENCE_FIELDS = {
    "frequency",
    "run_time",
    "day_of_week",
    "day_of_month",
    "timezone",
}


class ScanScheduleService:

    @staticmethod
    async def create_schedule(
        db: AsyncSession,
        user_id: UUID,
        request: ScanScheduleCreate,
    ) -> ScanSchedule:
        verified_domain = await DomainRepository.get_by_id(
            db,
            request.verified_domain_id,
            user_id
        )

        if verified_domain is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Verified domain not found",
            )

        if (verified_domain.status != DomainVerificationStatus.VERIFIED):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Scheduled scans require a verified domain",
            )

        frequency = ScanScheduleFrequency(request.frequency)

        next_run_at = calculate_next_run(
            frequency=frequency,
            run_time=request.run_time,
            day_of_week=request.day_of_week,
            day_of_month=request.day_of_month,
            timezone_name=request.timezone,
        )

        try:
            schedule = await ScanScheduleRepository.create_schedule(
                db,
                user_id=user_id,
                verified_domain_id=request.verified_domain_id,
                scan_type=request.scan_type,
                frequency=frequency,
                run_time=request.run_time,
                day_of_week=request.day_of_week,
                day_of_month=request.day_of_month,
                timezone_name=request.timezone,
                next_run_at=next_run_at,
            )

            await db.commit()
            await db.refresh(schedule)

            return schedule

        except IntegrityError as err:
            await db.rollback()

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A schedule already exists for this domain",
            ) from err


    @staticmethod
    async def list_schedules(
        db: AsyncSession,
        user_id: UUID,
    ) -> list[ScanSchedule]:
        return await ScanScheduleRepository.list_for_user(
            db,
            user_id=user_id,
        )


    @staticmethod
    async def get_schedule(
        db: AsyncSession,
        schedule_id: UUID,
        user_id: UUID,
    ) -> ScanSchedule:
        schedule = await ScanScheduleRepository.get_for_user(
            db,
            schedule_id=schedule_id,
            user_id=user_id,
        )

        if schedule is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scan schedule not found",
            )

        return schedule


    @staticmethod
    async def update_schedule(
        db: AsyncSession,
        schedule_id: UUID,
        user_id: UUID,
        request: ScanScheduleUpdate,
    ) -> ScanSchedule:
        schedule = await ScanScheduleService.get_schedule(
            db,
            schedule_id=schedule_id,
            user_id=user_id,
        )

        changes = request.model_dump(exclude_unset=True)

        if not changes:
            return schedule

        verified_domain = await DomainRepository.get_by_id(
            db,
            schedule.verified_domain_id,
            user_id,
        )

        if verified_domain is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Verified domain not found",
            )

        requested_active = changes.get(
            "is_active",
            schedule.is_active,
        )

        if (
            requested_active and verified_domain.status 
            != DomainVerificationStatus.VERIFIED
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="A schedule can only be active for a verified domain",
            )

        frequency = ScanScheduleFrequency(
            changes.get("frequency", schedule.frequency)
        )

        run_time = changes.get(
            "run_time",
            schedule.run_time,
        )


        day_of_week = changes.get(
            "day_of_week",
            schedule.day_of_week,
        )

        day_of_month = changes.get(
            "day_of_month",
            schedule.day_of_month,
        )

        timezone_name = changes.get(
            "timezone",
            schedule.timezone,
        )

        if "frequency" in changes:
            if frequency == ScanScheduleFrequency.WEEKLY:
                day_of_month = None
            else:
                day_of_week = None

        try:
            validate_schedule(
                frequency=frequency,
                run_time=run_time,
                day_of_week=day_of_week,
                day_of_month=day_of_month,
                timezone_name=timezone_name,
            )

        except ScheduleValidationError as err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(err),
            ) from err

        was_active = schedule.is_active

        schedule.frequency = frequency
        schedule.run_time = run_time
        schedule.day_of_week = day_of_week
        schedule.day_of_month = day_of_month
        schedule.timezone = timezone_name
        schedule.is_active = requested_active

        recurrence_changed = bool(RECURRENCE_FIELDS.intersection(changes))

        resumed = not was_active and requested_active

        if recurrence_changed or resumed:
            schedule.next_run_at = calculate_next_run(
                frequency=frequency,
                run_time=run_time,
                day_of_week=day_of_week,
                day_of_month=day_of_month,
                timezone_name=timezone_name,
                after=datetime.now(timezone.utc),
            )

        await db.commit()
        await db.refresh(schedule)

        return schedule


    @staticmethod
    async def delete_schedule(
        db: AsyncSession,
        schedule_id: UUID,
        user_id: UUID,
    ) -> None:
        schedule = await ScanScheduleService.get_schedule(
            db,
            schedule_id=schedule_id,
            user_id=user_id,
        )

        await ScanScheduleRepository.delete_schedule(
            db,
            schedule
        )
        await db.commit()


    @staticmethod
    async def dispatch_due_schedules(
        db: AsyncSession,
        batch_size: int = 20,
    ) -> int:

        dispatched = 0

        for _ in range(batch_size):
            now = datetime.now(timezone.utc)

            schedule = await ScanScheduleRepository.get_next_due(
                db,
                due_at=now,
            )

            if schedule is None:
                await db.rollback()
                break

            try:
                verified_domain = schedule.verified_domain

                domain_is_valid = (
                    verified_domain is not None
                    and verified_domain.user_id == schedule.user_id
                    and verified_domain.status == DomainVerificationStatus.VERIFIED
                )

                if not domain_is_valid:
                    schedule.is_active = False
                    await db.commit()

                    logger.warning(
                        "Schedule paused %s as domain verification is on longer valid",
                        schedule.id,
                    )
                    continue

                scheduled_for = schedule.next_run_at

                scan = (
                    await ScanScheduleRepository.get_or_create_occurrence(
                        db,
                        schedule=schedule,
                        scheduled_for=scheduled_for,
                    )
                )

                if scan.task_id is None:
                    await ScanService.publish_scan_task(
                        db,
                        scan,
                    )

                schedule.last_run_at = scheduled_for

                reference = max(now, scheduled_for)

                schedule.next_run_at = calculate_next_run(
                    frequency=schedule.frequency,
                    run_time=schedule.run_time,
                    day_of_week=schedule.day_of_week,
                    day_of_month=schedule.day_of_month,
                    timezone_name=schedule.timezone,
                    after=reference,
                )

                await db.commit()
                dispatched += 1

            except Exception:
                await db.rollback()

                logger.exception(
                    "Failed to dispatch scan schedule %s",
                    schedule.id,
                )

                raise

        return dispatched