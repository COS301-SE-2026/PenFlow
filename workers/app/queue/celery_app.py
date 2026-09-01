import os
import ssl
from urllib.parse import quote
from kombu import Queue

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


SCAN_QUEUE = Queue(
    "scans",
    routing_key="scans",
    durable=True,
    queue_arguments={"x-queue-type": "quorum"},
)

celery_app = Celery(
    "penflow_workers",
    broker=build_broker_url(),
    include=[
        "app.tasks.report_tasks",
        "app.tasks.dns_tasks",
        "app.tasks.urlscan_tasks",
        "app.tasks.wappalyzer_tasks",
        "app.tasks.crtsh_tasks",
        "app.tasks.shodan_tasks",
        "app.tasks.hibp_tasks",
        "app.tasks.target_resolution_task",
        "app.tasks.nmap_task",
        "app.tasks.http_security_task",
        "app.tasks.tls_task",
        "app.tasks.fingerprinting_task",
        "app.tasks.cpe_resolver_task",
        "app.tasks.cve_task",
        "app.tasks.full_scan_tasks",
    ],
)

celery_app.conf.update(
    task_default_queue="scans",
    task_default_queue_type="quorum",
    task_queues=(SCAN_QUEUE,),
    task_routes={
        "scan.*": {
            "queue": "scans",
            "routing_key": "scans",
        },
    },
    worker_detect_quorum_queues=True,
    broker_transport_options={
        "confirm_publish": True,
    },
)

if os.getenv("RABBITMQ_PROTOCOL", "amqps") == "amqps":
    celery_app.conf.broker_use_ssl = {
        "cert_reqs": ssl.CERT_REQUIRED,
    }

@celery_app.task(name="health_check")
def health_check() -> str:
    return "Worker is alive"
