from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.report import Report
from app.models.report_status import ReportStatus
from app.models.scan import Scan


def get_report_by_scan_id(db: Session, scan_id: str) -> Report | None:
    return db.query(Report).filter(Report.scan_id == UUID(scan_id)).first()


def get_or_create_report(db: Session, scan_id: str) -> Report:
    report = get_report_by_scan_id(db, scan_id)

    if report:
        return report

    report = Report(scan_id=UUID(scan_id), status=ReportStatus.PENDING)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def mark_report_generating(db: Session, scan_id: str) -> Report:
    report = get_or_create_report(db, scan_id)
    report.status = ReportStatus.GENERATING
    report.error_message = None

    db.commit()
    db.refresh(report)
    return report


def mark_report_task_queued(db: Session, scan_id: str, task_id: str) -> Report:
    report = get_or_create_report(db, scan_id)
    report.task_id = task_id
    report.status = ReportStatus.GENERATING
    report.error_message = None

    db.commit()
    db.refresh(report)
    return report


def mark_report_completed(db: Session, scan_id: str, pdf_path: str) -> Report:
    report = get_or_create_report(db, scan_id)
    report.status = ReportStatus.COMPLETED
    report.pdf_path = pdf_path
    report.generated_at = datetime.now(timezone.utc)
    report.error_message = None

    db.commit()
    db.refresh(report)
    return report


def mark_report_failed(db: Session, scan_id: str, error_message: str) -> Report:
    report = get_or_create_report(db, scan_id)
    report.status = ReportStatus.FAILED
    report.error_message = error_message

    db.commit()
    db.refresh(report)
    return report


def load_report_data(db: Session, scan_id: str) -> dict:
    scan = db.query(Scan).filter(Scan.id == UUID(scan_id)).first()

    if scan is None:
        raise ValueError(f"Scan not found: {scan_id}")

    return {
        "scan": scan,
        "findings": scan.findings,
        "scan_sources": scan.sources,
        "report": get_or_create_report(db, scan_id),
    }