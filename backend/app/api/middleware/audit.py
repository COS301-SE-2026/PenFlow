import asyncio
import logging
from uuid import UUID

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.config.database import SessionLocal
from app.models.evidence_file import EvidenceFile
from app.models.finding import Finding
from app.models.report import Report
from app.models.user import User
from app.repositories.audit_repository import AuditRepository

logger = logging.getLogger(__name__)

_PREFIXES = (
    "/api/v1/reports",
    "/api/v1/engagements",
    "/api/v1/service-delivery",
    "/api/v1/findings",
    "/api/v1/retests",
)


def event_for(request: Request, status: int) -> str | None:
    if not request.url.path.startswith(_PREFIXES):
        return None

    if request.scope.get("route") is None:
        return None

    if request.url.path.startswith("/api/v1/reports/"):
        if getattr(request.state, "audit_phase3_report", False) is not True:
            return None

    if status in {401, 403, 404}:
        return "sensitive_request.rejected"

    if request.method == "GET" and status == 200:
        if request.url.path.endswith("/pdf"):
            return "report.download_authorised"

        if request.url.path.endswith("/download"):
            return (
                "evidence.download_authorised"
                if "evidence_id" in request.path_params
                else "report.download_authorised"
            )

    return None


async def record_event(
        request: Request,
        action: str,
        status: int,
) -> None:
    route = request.scope["route"]

    metadata: dict[str, object] = {
        "route": route.path,
        "method": request.method,
        "status": status,
    }

    ids: dict[str, UUID] = {}

    for key in (
        "engagement_id",
        "finding_id",
        "evidence_id",
        "report_id",
    ):
        value = request.path_params.get(key)

        if value is not None:
            try:
                ids[key] = UUID(str(value))
                metadata[key] = str(ids[key])
            except ValueError:
                pass

    async with SessionLocal() as db:
        subject = getattr(request.state, "audit_subject", None)
        user_id = None

        if isinstance(subject, str):
            user_id = await db.scalar(
                select(User.id).where(
                    User.auth_provider == "keycloak",
                    User.auth_provider_id == subject,
                )
            )

        if status == 200:
            if "report_id" in ids:
                report = await db.get(Report, ids["report_id"])

                if report is not None and report.engagement_id is not None:
                    metadata["engagement_id"] = str(report.engagement_id)

            if "evidence_id" in ids:
                evidence = await db.get(EvidenceFile, ids["evidence_id"])

                if evidence is not None:
                    finding = await db.get(Finding, evidence.finding_id)

                    if finding is not None and finding.engagement_id is not None:
                        metadata["engagement_id"] = str(finding.engagement_id)

        await AuditRepository.create_log(
            db,
            user_id=user_id,
            action=action,
            entity_type="http_request",
            entity_id=None,
            metadata=metadata,
        )


async def audit_sensitive_requests(
        request: Request,
        call_next: RequestResponseEndpoint,
) -> Response:
    response = await call_next(request)
    action = event_for(request, response.status_code)

    if action is None:
        return response

    try:
        await asyncio.wait_for(
            record_event(request, action, response.status_code),
            timeout=2.0,
        )

    except Exception:
        logger.exception(
            "Sensitive request audit write failed: %s",
            action,
        )

        if action.endswith("download_authorised"):
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "Download auditing is temporarily unavailable",
                },
                headers={"Cache-Control": "no-store"},
            )

    return response