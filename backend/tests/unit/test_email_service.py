from unittest.mock import MagicMock, patch

import pytest

from app.services.email_service import EmailDeliveryError, send_report_email


@patch("app.services.email_service.smtplib.SMTP")
def test_send_report_email_success(mock_smtp, tmp_path, monkeypatch):
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")

    monkeypatch.setenv("SMTP_FROM", "test@penflow.test")
    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    monkeypatch.setenv("SMTP_USER", "user")
    monkeypatch.setenv("SMTP_PASSWORD", "password")
    monkeypatch.setenv("SMTP_PORT", "587")

    smtp_inst = MagicMock()
    mock_smtp.return_value.__enter__.return_value = smtp_inst
    send_report_email(
        to_email="customer@test.com", 
        domain="example.com", 
        storage_ref=str(pdf),
    )

    smtp_inst.starttls.assert_called_once()
    smtp_inst.login.assert_called_once_with("user", "password")
    smtp_inst.send_message.assert_called_once()


def test_send_report_email_missing_smtp_env(tmp_path, monkeypatch):
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")

    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)

    with pytest.raises(EmailDeliveryError, match="SMTP env variables are missing"):
        send_report_email(
            to_email="customer@test.com", 
            domain="example.com", 
            storage_ref=str(pdf),
        )
