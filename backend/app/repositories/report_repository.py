from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

JSONDict = dict[str, Any]
JSONList = list[JSONDict]

def fetch_singular_row_as_dict(db: Session, query: str, params: JSONDict) -> JSONDict | None:
    row = db.execute(text(query), params).mappings().first()
    return dict(row) if row else None


def fetch_all_rows_as_dicts(db: Session, query: str, params: JSONDict) -> JSONList:
    rows = db.execute(text(query), params).mappings().all()
    return [dict(row) for row in rows]


def load_scan_by_id(db: Session, scan_id: str) -> JSONDict | None:
    return fetch_singular_row_as_dict(
        db,
        """
        SELECT *
        FROM scans
        WHERE id = :scan_id
        """,
        {"scan_id": scan_id},
    )


def load_findings_by_scan_id(db: Session, scan_id: str) -> JSONList:
    return fetch_all_rows_as_dicts(
        db,
        """
        SELECT *
        FROM findings
        WHERE scan_id = :scan_id
        ORDER BY
            CASE severity
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                WHEN 'low' THEN 4
                WHEN 'info' THEN 5
                ELSE 6
            END,
            created_at ASC
        """,
        {"scan_id": scan_id},
    )


def load_scan_sources_by_scan_id(db: Session, scan_id: str) -> JSONList:
    return fetch_all_rows_as_dicts(
        db,
        """
        SELECT *
        FROM scan_sources
        WHERE scan_id = :scan_id
        ORDER BY source_name ASC
        """,
        {"scan_id": scan_id},
    )


def get_report_by_scan_id(db: Session, scan_id: str) -> JSONDict | None:
    return fetch_singular_row_as_dict(
        db,
        """
        SELECT *
        FROM reports
        WHERE scan_id = :scan_id
        LIMIT 1
        """,
        {"scan_id": scan_id},
    )


def create_report_by_scan_id(db: Session, scan_id: str) -> JSONDict | None:
    report = fetch_singular_row_as_dict(
        db,
        """
        INSERT INTO reports (scan_id, status)
        VALUES (:scan_id, 'pending')
        RETURNING *
        """,
        {"scan_id": scan_id},
    )
    db.commit()
    return report


def get_or_create_report(db: Session, scan_id: str) -> JSONDict | None:
    report = get_report_by_scan_id(db, scan_id)

    if report:
        return report

    return create_report_by_scan_id(db, scan_id)


def mark_report_generating(db: Session, scan_id: str) -> JSONDict | None:
    get_or_create_report(db, scan_id)

    report = fetch_singular_row_as_dict(
        db,
        """
        UPDATE reports
        SET status = 'generating',
            error_message = NULL
        WHERE scan_id = :scan_id
        RETURNING *
        """,
        {"scan_id": scan_id},
    )
    db.commit()
    return report


def mark_report_completed(db: Session, scan_id: str, pdf_path: str) -> JSONDict | None:
    report = fetch_singular_row_as_dict(
        db,
        """
        UPDATE reports
        SET status = 'completed',
            pdf_path = :pdf_path,
            generated_at = NOW(),
            error_message = NULL
        WHERE scan_id = :scan_id
        RETURNING *
        """,
        {
            "scan_id": scan_id,
            "pdf_path": pdf_path,
        },
    )
    db.commit()
    return report


def mark_report_failed(db: Session, scan_id: str, error_message: str) -> JSONDict | None:
    get_or_create_report(db, scan_id)

    report = fetch_singular_row_as_dict(
        db,
        """
        UPDATE reports
        SET status = 'failed',
            error_message = :error_message
        WHERE scan_id = :scan_id
        RETURNING *
        """,
        {
            "scan_id": scan_id,
            "error_message": error_message,
        },
    )
    db.commit()
    return report


def load_report_data(db: Session, scan_id: str) -> JSONDict:
    scan = load_scan_by_id(db, scan_id)

    if scan is None:
        raise ValueError(f"Scan not found: {scan_id}")

    return {
        "scan": scan,
        "findings": load_findings_by_scan_id(db, scan_id),
        "scan_sources": load_scan_sources_by_scan_id(db, scan_id),
        "report": get_or_create_report(db, scan_id),
    }


def mark_report_task_queued(db: Session, scan_id: str, task_id: str) -> JSONDict | None:
    report = fetch_singular_row_as_dict(
        db,
        """
        UPDATE reports
        SET task_id = :task_id,
            status = 'generating',
            error_message = NULL
        WHERE scan_id = :scan_id
        RETURNING *
        """,
        {"scan_id": scan_id, "task_id": task_id},
    )
    db.commit()
    return report