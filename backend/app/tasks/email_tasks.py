import logging

from app.queue.celery_app import celery_app
from app.services.email_service import (
    EmailDeliveryError,
    send_email,
    send_report_email
)

logger = logging.getLogger(__name__)

@celery_app.task(
    name="email.send",
    autoretry_for=(EmailDeliveryError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def send_email_task(
    to_email: str,
    subject: str,
    text_body: str,
) -> None:
    logger.info("Sending email to %s", to_email)

    send_email(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
    )

@celery_app.task(
    name="email.report",
    autoretry_for=(EmailDeliveryError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def send_report_email_task(
    to_email: str,
    domain: str,
    storage_ref: str,
) -> None:
    logger.info("Sending report email for domain %s to %s", domain, to_email)

    send_report_email(
        to_email=to_email,
        domain=domain,
        storage_ref=storage_ref
    )