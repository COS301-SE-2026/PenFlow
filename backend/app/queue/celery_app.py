import os

from celery import Celery

celery_app = Celery(
    "penflow_backend",
    broker=os.getenv("RABBITMQ_URL"),
    backend=os.getenv("REDIS_URL"),
)