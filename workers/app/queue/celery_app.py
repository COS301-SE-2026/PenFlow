import os

from celery import Celery

celery_app = Celery(
    "penflow_workers",
    broker=os.getenv("RABBITMQ_URL"),
    backend=os.getenv("REDIS_URL"),
    include=[
        "app.tasks.report_tasks",
        "app.tasks.dns_tasks",
    ],
)

@celery_app.task(name="health_check")
def health_check() -> str:
    return "Worker is alive"