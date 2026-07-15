import os

from celery import Celery

celery_app = Celery(
    "penflow_workers",
    broker=os.getenv("RABBITMQ_URL"),
    backend=os.getenv("REDIS_URL"),
    include=[
        "app.tasks.report_tasks",
        "app.tasks.dns_tasks",
        "app.tasks.urlscan_tasks",
        "app.tasks.wappalyzer_tasks",
        "app.tasks.crtsh_tasks",
        "app.tasks.shodan_tasks",
        "app.tasks.hunter_tasks",
        "app.tasks.hibp_tasks",
        "app.tasks.domain_verification_task",
        "app.tasks.target_resolution_task",
        "app.tasks.nmap_task",
        "app.tasks.http_security_task",
        "app.tasks.tls_task",
        "app.tasks.full_scan_tasks",
    ],
)

@celery_app.task(name="health_check")
def health_check() -> str:
    return "Worker is alive"