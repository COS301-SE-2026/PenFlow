import logging
from pathlib import Path
from typing import Any

from app.queue.celery_app import celery_app
from app.services.pdf_render_service import generate_pdf_from_html

JSONDict = dict[str, Any]

logger = logging.getLogger(__name__)


@celery_app.task(name="render_report")
def render_report_pdf_task(scan_id: str, html_content: str, output_path: str) -> JSONDict:
    try:
        pdf_path = generate_pdf_from_html(
            html_content=html_content,
            output_path=Path(output_path),
        )

        logger.info(
            "Report PDF rendered successfully for scan %s: %s",
            scan_id,
            pdf_path,
        )

        return {
            "status": "completed",
            "scan_id": scan_id,
            "pdf_path": str(pdf_path),
        }

    except Exception as error:
        logger.exception(
            "Report PDF rendering failed for scan %s",
            scan_id,
        )

        return {
            "status": "failed",
            "scan_id": scan_id,
            "error": str(error),
        }