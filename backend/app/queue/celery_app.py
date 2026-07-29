import os
import ssl
from urllib.parse import quote

from celery import Celery


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

celery_app = Celery(
    "penflow_backend",
    broker=build_broker_url(),
)

celery_app.conf.update(
    task_default_queue="celery",
    task_default_queue_type="quorum",
    broker_transport_options={
        "confirm_publish": True,
    },
)

if os.getenv("RABBITMQ_PROTOCOL", "amqps") == "amqps":
    celery_app.conf.broker_use_ssl = {
        "cert_reqs": ssl.CERT_REQUIRED,
    }
