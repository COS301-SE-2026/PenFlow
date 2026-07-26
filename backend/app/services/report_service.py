import os
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import ScanType
from app.queue.celery_app import celery_app
from app.repositories.report_repository import (
    load_report_data,
    mark_report_failed,
    mark_report_generating,
    mark_report_task_queued,
)
from app.utils.report_context import build_report_context
from app.utils.phase2_report_context import build_phase2_report_context

BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = BASE_DIR / "templates"

REPORT_OUTPUT_DIR = Path(
    os.getenv("REPORT_OUTPUT_DIR", str(BASE_DIR.parent / "generated_reports"))
)

REPORT_TEMPLATE_NAME = {
    ScanType.PASSIVE_CTEM: "passive_report_template.html",
    ScanType.ACTIVE_VULNERABILITY: "phase2_report_template.html"
}


def get_template_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def render_report_html(scan_type: ScanType, context: dict[str, Any]) -> str:
    template_name = REPORT_TEMPLATE_NAME.get(scan_type)

    if template_name is None:
        raise ValueError(f"No report template for scan type: {scan_type.value}")

    template_env = get_template_environment()
    template = template_env.get_template(template_name)

    return str(template.render(**context))


def build_report_output_path(scan_id: str) -> Path:
    REPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return REPORT_OUTPUT_DIR / f"penflow_report_{scan_id}.pdf"


async def queue_report_generation(db: AsyncSession, scan_id: str) -> dict[str, Any]:
    try:
        await mark_report_generating(db, scan_id)

        report_data = await load_report_data(db, scan_id)

        scan = report_data["scan"]

        if scan.scan_type == ScanType.PASSIVE_CTEM:
            context = build_report_context(
                scan=scan,
                findings=report_data["findings"],
                scan_sources=report_data["scan_sources"],
            )

        elif scan.scan_type == ScanType.ACTIVE_VULNERABILITY:
            context = build_phase2_report_context(
                scan=scan,
                findings=report_data["findings"],
                assets=report_data["assets"],
                services=report_data["services"],
                technologies=report_data["technologies"],
            )

        else:
            raise ValueError(f"Unknown scan type: {scan.scan_type}")

        html_content = render_report_html(
            scan_type = scan.scan_type,
            context = context,
        )
        output_path = build_report_output_path(scan_id)

        task = celery_app.send_task(
            "scan.render_report",
            args=[scan_id, html_content, str(output_path)],
        )

        await mark_report_task_queued(db, scan_id, task.id)

        return {
            "scan_id": scan_id,
            "task_id": task.id,
            "pdf_path": str(output_path),
            "status": "generating",
        }

    except Exception as error:
        await mark_report_failed(db, scan_id, str(error))
        raise
