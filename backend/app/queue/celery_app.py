import os
import urllib.parse import quote

from celery import Celery

def build_broker_url() -> str:

    host = os.getenv("RABBITMQ_HOST")
    port = os.getenv("RABBITMQ_PORT", "5671")
    username = os.getenv("RABBITMQ_USERNAME")
    password = os.getenv("RABBITMQ_PASSWORD")

    if not host or not username or not password:
        raise RuntimeError("RabbitMQ environment variables are missing")

    return (
        f"amqps://{quote(username, safe='')}:"
        f"{quote(password, safe='')}@"
        f"{host}:{port}//"
    )

celery_app = Celery(
    "penflow_backend",
    broker=build_broker_url(),
)