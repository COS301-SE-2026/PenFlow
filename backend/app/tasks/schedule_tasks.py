import asyncio
from asyncio import AbstractEventLoop
from typing import Any

from app.queue.celery_app import celery_app
from app.services.scan_schedule_service import ScanScheduleService

task_loop: AbstractEventLoop | None = None

def get_task_loop() -> AbstractEventLoop:
    global task_loop

    if task_loop is None or task_loop.is_closed():
        task_loop = asyncio.new_event_loop()

    return task_loop


async def dispatch_due() -> dict[str, Any]:
    from app.config.database import SessionLocal

    async with SessionLocal() as db:
        dispatched = await ScanScheduleService.dispatch_due_schedules(db)

        return {
            "status": "completed",
            "dispatched": dispatched,
        }


@celery_app.task(
    bind=True,
    name="schedules.dispatch_due",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def dispatch_due_schedules_task(task: Any) -> dict[str, Any]:
    loop = get_task_loop()
    return loop.run_until_complete(dispatch_due())