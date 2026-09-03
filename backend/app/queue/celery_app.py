import os
import ssl
from urllib.parse import quote

from celery import Celery
from kombu import Exchange, Queue  # type: ignore[import-untyped]


def build_broker_url() -> str:

    protocol = os.getenv("RABBITMQ_PROTOCOL", "amqps")
    host = os.getenv("RABBITMQ_HOST")
    port = os.getenv("RABBITMQ_PORT", "5671")
    username = os.getenv("RABBITMQ_USERNAME")
    password = os.getenv("RABBITMQ_PASSWORD")

    if not host or not username or not password:
        raise RuntimeError("RabbitMQ environment variables are missing")

    return (
        f"{protocol}://{quote(username, safe='')}:"
        f"{quote(password, safe='')}@"
        f"{host}:{port}//"
    )


SCAN_EXCHANGE = Exchange(
    "scans",
    type="direct",
    durable=True,
)

EMAIL_EXCHANGE = Exchange(
    "email",
    type="direct",
    durable=True,
)

SCHEDULE_EXCHANGE = Exchange(
    "schedules",
    type="direct",
    durable=True,
)


SCAN_QUEUE = Queue(
    "scans",
    exchange=SCAN_EXCHANGE,
    routing_key="scans",
    durable=True,
    queue_arguments={"x-queue-type": "quorum"},
)

EMAIL_QUEUE = Queue(
    "email",
    exchange=EMAIL_EXCHANGE,
    routing_key="email",
    durable=True,
    queue_arguments={"x-queue-type": "quorum"},
)

SCHEDULE_QUEUE = Queue(
    "schedules",
    exchange=SCHEDULE_EXCHANGE,
    routing_key="schedules",
    durable=True,
    queue_arguments={"x-queue-type": "quorum"},
)

celery_app = Celery(
    "penflow_backend",
    broker=build_broker_url(),
    include=[
        "app.tasks.email_tasks",
        "app.tasks.schedule_tasks",
    ],
)

celery_app.conf.update(
    task_default_queue="scans",
    task_default_queue_type="quorum",
    task_queues=(
        SCAN_QUEUE,
        EMAIL_QUEUE,
        SCHEDULE_QUEUE,
    ),
    broker_transport_options={
        "confirm_publish": True,
    },
    task_routes={
        "scan.*": {
            "queue": "scans",
            "routing_key": "scans",
        },
        "email.*": {
            "queue": "email",
            "routing_key": "email",
        },
        "schedules.*": {
            "queue": "schedules",
            "routing_key": "schedules",
        },
    },
    beat_schedule = {
        "dispatch-due-scan-schedules": {
            "task": "schedules.dispatch_due",
            "schedule": 60.0,
        },
    },
    timezone="UTC",
)

if os.getenv("RABBITMQ_PROTOCOL", "amqps") == "amqps":
    celery_app.conf.broker_use_ssl = {
        "cert_reqs": ssl.CERT_REQUIRED,
    }
