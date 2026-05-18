from sqlalchemy import text
from sqlalchemy.orm import Session


def fetch_singular_row_as_dict(db: Session, query: str, params: dict):
    row = db.execute(text(query), params).mappings().first()
    return dict(row) if row else None


def fetch_all_rows_as_dicts(db: Session, query: str, params: dict):
    rows = db.execute(text(query), params).mappings().all()
    return [dict(row) for row in rows]


def load_scan_by_id(db: Session, scan_id: str):
    return fetch_singular_row_as_dict(
        db,
        """
        SELECT *
        FROM scans
        WHERE id = :scan_id
        """,
        {"scan_id": scan_id},
    )


def load_findings_by_scan_id(db: Session, scan_id: str):
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


def load_scan_sources_by_scan_id(db: Session, scan_id: str):
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


def get_report_by_scan_id(db: Session, scan_id: str):
    return fetch_one_as_dict(
        db,
        """
        SELECT *
        FROM reports
        WHERE scan_id = :scan_id
        LIMIT 1
        """,
        {"scan_id": scan_id},
    )


def create_report_by_scan_id(db: Session, scan_id: str):
    report = fetch_one_as_dict(
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


def get_or_create_report(db: Session, scan_id: str):
    report = get_report_by_scan_id(db, scan_id)

    if report:
        return report

    return create_report_by_scan_id(db, scan_id)

