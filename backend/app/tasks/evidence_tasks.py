from app.queue.celery_app import celery_app
from app.services.evidence_quarantine_service import EvidenceQuarantineService


async def process_pending() -> dict[str, bool]:
    from app.config.database import SessionLocal

    async with SessionLocal() as db:
        return {
            "processed": await EvidenceQuarantineService.process_one(db)
        }


@celery_app.task(
    name="evidence.scan_pending",
    acks_late=True,
    reject_on_worker_lost=True,
    ignore_result=True,
)
def scan_pending_evidence_task() -> dict[str, bool]:
    from app.tasks.schedule_tasks import get_task_loop

    return get_task_loop().run_until_complete(process_pending())