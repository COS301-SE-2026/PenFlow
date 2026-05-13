import os

from celery import Celery

rabbitmq_url = os.getenv(
    "RABBITMQ_URL",
    "amqp://guest:guest@localhost:5672//",
)

celery_app = Celery(
    "penflow_workers",
    broker=rabbitmq_url,
)

@celery_app.task(name="health_check")
def health_check() -> str:
    return "Worker is alive"