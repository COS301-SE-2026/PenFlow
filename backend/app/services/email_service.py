import os
import smtplib
from email.message import EmailMessage

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.services.report_storage_service import ReportStorageService

class EmailDeliveryError(Exception):
    """Error is raised if an email cannot be delivered"""


def get_email_transport_method() -> str:
    return os.getenv("EMAIL_TRANSPORT", "smtp").lower()


def send_smtp_message(message: EmailMessage) -> None:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    if not smtp_host or not smtp_user or not smtp_password:
        raise EmailDeliveryError(
            "SMTP env variables are missing"
        )

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(message)

    except (OSError, smtplib.SMTPException) as err:
        raise EmailDeliveryError(
            "Failed to send email using SMTP"
        ) from err


def send_ses_message(message: EmailMessage) -> None:
    aws_region = os.getenv("AWS_REGION", "af-south-1")

    try:
        client = boto3.client(
            "sesv2",
            region_name=aws_region,
        )

        client.send_email(
            FromEmailAddress=str(message["From"]),
            Destination={
                "ToAddresses": [str(message["To"])],
            },
            Content={
                "Raw": {
                    "Data": message.as_bytes(),
                },
            },
        )

    except (BotoCoreError, ClientError) as err:
        raise EmailDeliveryError(
            "Failed to send email using Amazon SES"
        ) from err


def send_message(message: EmailMessage) -> None:
    transport = get_email_transport_method()

    if transport == "smtp":
        send_smtp_message(message)
        return

    if transport == "ses":
        send_ses_message(message)
        return

    raise EmailDeliveryError(
        f"Unsupported email transport method: {transport}"
    )


def get_sender() -> str:
    transport = get_email_transport_method()

    if transport == "smtp":
        sender = os.getenv("SMTP_FROM")

    elif transport == "ses":
        sender = os.getenv("EMAIL_FROM")

    else:
        raise EmailDeliveryError(
            f"Unsupported email transport method: {transport}"
        )

    if not sender:
        raise EmailDeliveryError(
            f"Sender email is not configured for {transport}"
        )

    return sender


def send_email(
        *,
        to_email: str,
        subject:str,
        text_body: str,
) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = get_sender()
    message["To"] = to_email
    message.set_content(text_body)

    send_message(message)


def send_report_email(
        *,
        to_email: str,
        domain: str,
        storage_ref: str,
) -> None:
    try:
        pdf_bytes = ReportStorageService.get_report_bytes(
            storage_ref,
        )

    except Exception as err:
        raise EmailDeliveryError(
            f"Failed to retrieve report for {domain}",
        ) from err

    message = EmailMessage()
    message["Subject"] = f"Your PenFlow CTEM Report for {domain}"
    message["From"] = get_sender()
    message["To"] = to_email

    message.set_content(
        f"Hi,\n\n"
        f"Your PenFlow CTEM report for {domain} is attached.\n\n"
        f"Regards,\n"
        f"PenFlow"
    )

    message.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=f"penflow-report-{domain}.pdf",
    )

    send_message(message)