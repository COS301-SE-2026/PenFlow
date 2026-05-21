import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


def send_report_email(destination_email: str, domain: str, pdf_path: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = f"Your PenFlow CTEM Report for {domain}"
    msg["From"] = os.getenv("SMTP_FROM")
    msg["To"] = destination_email

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

    with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT", "587"))) as server:
        server.starttls()
        server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
        server.send_message(msg)