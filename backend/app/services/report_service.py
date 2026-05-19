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