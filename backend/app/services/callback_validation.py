from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

from app.models.base import ReportStatus
from app.models.report import Report
from app.schemas.report import ReportCallbackRequest
from app.services.report_service import REPORT_OUTPUT_DIR
from app.services.report_storage_service import REPORT_STORAGE


def validated_report_reference(
    report: Report,
    supplied: str | None,
) -> str:
    if not supplied:
        raise HTTPException(422, "pdf_path is required")

    if (
        report.scan_id is not None
        and report.engagement_id is None
    ):
        identifier = str(report.scan_id)

        keys = {
            f"scans/{identifier}/report.pdf",
            f"reports/{identifier}/report.pdf",
        }

        filename = f"penflow_report_{identifier}.pdf"

    elif (
        report.engagement_id is not None
        and report.scan_id is None
    ):
        identifier = str(report.engagement_id)

        keys = {
            f"engagements/{identifier}/reports/v{report.version}.pdf",
        }

        filename = (
            f"engagement_report_{identifier}_v{report.version}.pdf"
        )

    else:
        raise HTTPException(409, "Invalid report association")

    if REPORT_STORAGE == "s3":
        if supplied not in keys:
            raise HTTPException(
                422,
                "Invalid report storage reference",
            )

        return supplied

    if REPORT_STORAGE == "local":
        expected = (
            REPORT_OUTPUT_DIR.resolve() / filename
        ).resolve()

        try:
            actual = Path(supplied).resolve()
        except (OSError, ValueError, RuntimeError) as exc:
            raise HTTPException(
                422,
                "Invalid report storage reference",
            ) from exc

        if actual != expected:
            raise HTTPException(
                422,
                "Invalid report storage reference",
            )

        return str(expected)

    raise RuntimeError("Unsupported report storage mode")


def apply_report_callback(
    report: Report,
    payload: ReportCallbackRequest,
) -> bool:
    if payload.status not in {"completed", "failed"}:
        raise HTTPException(
            422,
            "Invalid report callback status",
        )

    reference = (
        validated_report_reference(report, payload.pdf_path)
        if payload.status == "completed"
        else None
    )

    target = ReportStatus(payload.status)

    if report.status == target:
        if (
            target == ReportStatus.COMPLETED
            and report.pdf_path != reference
        ):
            raise HTTPException(
                409,
                "Report is already complete",
            )

        return False

    if report.status not in {
        ReportStatus.PENDING,
        ReportStatus.GENERATING,
    }:
        raise HTTPException(
            409,
            "Invalid report status transition",
        )

    report.status = target
    report.pdf_path = reference
    report.generated_at = (
        datetime.now(timezone.utc)
        if target == ReportStatus.COMPLETED
        else None
    )
    report.error_message = (
        payload.error_message or "Report generation failed"
        if target == ReportStatus.FAILED
        else None
    )

    return True