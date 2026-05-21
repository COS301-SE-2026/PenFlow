import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


def send_report_email(to_email: str, domain: str, pdf_path: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = f"Your PenFlow CTEM Report for {domain}"
    msg["From"] = os.getenv("SMTP_FROM")
    msg["To"] = to_email

    msg.set_content(
        f"Hi,\n\nYour PenFlow CTEM report for {domain} is attached.\n\nRegards,\nPenFlow"
    )

    pdf_file = Path(pdf_path)
    msg.add_attachment(
        pdf_file.read_bytes(),
        maintype="application",
        subtype="pdf",
        filename=pdf_file.name,
    )

    smtp_host = os.getenv("SMTP_HOST")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not smtp_host or not smtp_user or not smtp_password:
        raise ValueError("SMTP environment variables are missing")

    with smtplib.SMTP(smtp_host, int(os.getenv("SMTP_PORT", "587"))) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)