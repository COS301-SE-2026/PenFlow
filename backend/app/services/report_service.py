import os

from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from app.repositories.report_repository import (
    load_report_data,
    mark_report_completed,
    mark_report_failed,
    mark_report_generating,
    mark_report_task_queued,
)

from app.services.pdf_renderer import generate_pdf_from_html
from app.utils.report_context import build_report_context
from celery.result import AsyncResult
from app.queue.celery_app import celery_app


BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = BASE_DIR / "templates"

REPORT_OUTPUT_DIR = Path(
    os.getenv("REPORT_OUTPUT_DIR", str(BASE_DIR.parent / "generated_reports"))
)

REPORT_TEMPLATE_NAME = "report_template.html"


def get_template_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def render_report_html(context: dict) -> str:
    template_env = get_template_environment()
    template = template_env.get_template(REPORT_TEMPLATE_NAME)

    return template.render(**context)


def build_report_output_path(scan_id: str) -> Path:
    REPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return REPORT_OUTPUT_DIR / f"ctem_report_{scan_id}.pdf"


# Serialized version of pdf gen that can be used for testing
def generate_report_pdf(db: Session, scan_id: str) -> str:
    try:
        mark_report_generating(db, scan_id)

        report_data = load_report_data(db, scan_id)

        context = build_report_context(
            scan=report_data["scan"],
            findings=report_data["findings"],
            scan_sources=report_data["scan_sources"],
        )

        html_content = render_report_html(context)
        output_path = build_report_output_path(scan_id)

        pdf_path = generate_pdf_from_html(
            html_content=html_content,
            output_path=output_path,
        )

        mark_report_completed(
            db=db,
            scan_id=scan_id,
            pdf_path=str(pdf_path),
        )

        return str(pdf_path)

    except Exception as error:
        mark_report_failed(
            db=db,
            scan_id=scan_id,
            error_message=str(error),
        )
        raise


def queue_report_generation(db: Session, scan_id: str) -> dict:
    try:
        mark_report_generating(db, scan_id)

        report_data = load_report_data(db, scan_id)

        context = build_report_context(
            scan=report_data["scan"],
            findings=report_data["findings"],
            scan_sources=report_data["scan_sources"],
        )

        html_content = render_report_html(context)
        output_path = build_report_output_path(scan_id)

        task = celery_app.send_task(
            "render_report",
            args=[scan_id, html_content, str(output_path)],
        )

        mark_report_task_queued(db, scan_id, task.id)

        return {
            "scan_id": scan_id,
            "task_id": task.id,
            "pdf_path": str(output_path),
            "status": "generating",
        }

    except Exception as error:
        mark_report_failed(db, scan_id, str(error))
        raise
