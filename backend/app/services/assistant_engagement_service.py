from datetime import date, timedelta
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import EngagementStatus, ReportStatus
from app.models.user import User
from app.repositories.report_repository import get_latest_for_engagement
from app.repositories.retest_repository import RetestRepository
from app.schemas.engagement import (
    EngagementListItem,
    EngagementSortField,
    SortOrder,
)
from app.services.engagement_service import EngagementService


class AssistantEngagementIntent(str, Enum):
    OVERVIEW = "engagement_overview"
    STATUS = "engagement_status"
    SCHEDULE = "engagement_schedule"
    ATTENTION = "engagement_attention"
    FINDINGS = "engagement_findings"
    ASSIGNMENT = "engagement_assignment"
    REPORT = "engagement_report"
    RETESTS = "engagement_retests"


class AssistantEngagementFinding(BaseModel):
    finding_id: UUID
    title: str
    severity: str
    status: str


class AssistantEngagementSummary(BaseModel):
    engagement_id: UUID
    title: str
    status: str
    priority: str
    engagement_type: str
    assessment_type: str
    scope: str | None = None
    asset_count: int = 0
    manual_finding_count: int | None = None
    automated_finding_count: int | None = None
    requested_start_date: date | None = None
    requested_end_date: date | None = None
    scheduled_start_date: date | None = None
    scheduled_end_date: date | None = None
    target_date: date | None = None
    client_name: str | None = None
    assigned_pentester_name: str | None = None
    service_delivery_name: str | None = None
    report_status: str | None = None
    report_available: bool | None = None
    open_retest_count: int | None = None
    recent_findings: list[
        AssistantEngagementFinding
    ] = Field(default_factory=list)
    attention_reasons: list[str] = Field(
        default_factory=list
    )
    href: str


def enum_value(
        value: object,
) -> str:
    if isinstance(value, Enum):
        return str(value.value)

    return str(value)


def engagement_href(
        role: str,
        engagement_id: UUID,
) -> str:
    if role == "service_delivery":
        return (
            f"/service-delivery/engagements/"
            f"{engagement_id}"
        )

    if role in {"pentester", "admin"}:
        return (
            "/pentesting/console/my-engagements/"
            f"{engagement_id}/findings"
        )

    return f"/pentesting/engagement/{engagement_id}"


class AssistantEngagementService:
    @staticmethod
    def classify_intent(
        question: str,
    ) -> AssistantEngagementIntent:
        normalized = question.casefold()

        if any(
            phrase in normalized
            for phrase in (
                "report",
                "report available",
            )
        ):
            return AssistantEngagementIntent.REPORT

        if any(
            phrase in normalized
            for phrase in (
                "retest",
                "retests",
            )
        ):
            return AssistantEngagementIntent.RETESTS

        if any(
            phrase in normalized
            for phrase in (
                "finding",
                "findings",
                "vulnerability",
                "vulnerabilities",
            )
        ):
            return AssistantEngagementIntent.FINDINGS

        if any(
            phrase in normalized
            for phrase in (
                "assigned",
                "assignment",
                "pentester",
                "unassigned",
            )
        ):
            return AssistantEngagementIntent.ASSIGNMENT

        if any(
            phrase in normalized
            for phrase in (
                "require attention",
                "requires attention",
                "need attention",
                "needs attention",
                "need scheduling",
                "needs scheduling",
                "awaiting review",
                "work on next",
                "approaching",
                "due soon",
            )
        ):
            return AssistantEngagementIntent.ATTENTION

        if any(
            phrase in normalized
            for phrase in (
                "scheduled",
                "schedule",
                "start date",
                "end date",
                "when does",
                "when is",
            )
        ):
            return AssistantEngagementIntent.SCHEDULE

        if any(
            phrase in normalized
            for phrase in (
                "status",
                "in progress",
                "completed",
                "cancelled",
                "requested",
                "scoping",
                "review",
            )
        ):
            return AssistantEngagementIntent.STATUS

        return AssistantEngagementIntent.OVERVIEW


    @staticmethod
    def extract_status(
        question: str,
    ) -> EngagementStatus | None:
        normalized = question.casefold()

        status_phrases = (
            (
                EngagementStatus.IN_PROGRESS,
                ("in progress", "in-progress"),
            ),
            (
                EngagementStatus.REQUESTED,
                ("requested",),
            ),
            (
                EngagementStatus.SCOPING,
                ("scoping",),
            ),
            (
                EngagementStatus.SCHEDULED,
                ("scheduled",),
            ),
            (
                EngagementStatus.REVIEW,
                ("review",),
            ),
            (
                EngagementStatus.COMPLETED,
                ("completed", "complete"),
            ),
            (
                EngagementStatus.CANCELLED,
                ("cancelled", "canceled"),
            ),
        )

        for status, phrases in status_phrases:
            if any(
                phrase in normalized
                for phrase in phrases
            ):
                return status

        return None


    @staticmethod
    def project_list_item(
        item: EngagementListItem,
        role: str,
    ) -> AssistantEngagementSummary:
        return AssistantEngagementSummary(
            engagement_id=item.id,
            title=item.title,
            status=enum_value(item.status),
            priority=item.priority,
            engagement_type=enum_value(item.engagement_type),
            assessment_type=enum_value(item.assessment_type),
            asset_count=item.asset_count,
            requested_start_date=item.requested_start_date,
            requested_end_date=item.requested_end_date,
            scheduled_start_date=item.scheduled_start_date,
            scheduled_end_date=item.scheduled_end_date,
            target_date=item.target_date,
            client_name=item.client_name,
            assigned_pentester_name=item.assigned_pentester_name,
            href=engagement_href(role, item.id),
        )


    @staticmethod
    async def list_my_engagements(
        db: AsyncSession,
        user: User,
        engagement_status: EngagementStatus | None = None,
        limit: int = 10,
    ) -> list[AssistantEngagementSummary]:
        bounded_limit = max(1, min(limit, 20))

        result = await EngagementService.list_engagements(
            db,
            user_id=user.id,
            user_role=user.role,
            engagement_status=engagement_status,
            search=None,
            sort=EngagementSortField.UPDATED_AT,
            order=SortOrder.DESC,
            limit=bounded_limit,
            offset=0,
        )

        return [
            AssistantEngagementService.project_list_item(
                item,
                role=user.role,
            )
            for item in result.items
        ]


    @staticmethod
    async def get_engagement_summary(
        db: AsyncSession,
        user: User,
        engagement_id: UUID,
    ) -> AssistantEngagementSummary:
        detail = await EngagementService.get_engagement_detail(
            db,
            engagement_id=engagement_id,
            user_id=user.id,
        )

        report = await get_latest_for_engagement(
            db,
            engagement_id,
        )

        open_retest_count = (
            await RetestRepository.count_open_by_engagement(
                db,
                engagement_id,
            )
        )

        return AssistantEngagementSummary(
            engagement_id=detail.id,
            title=detail.title,
            status=enum_value(detail.status),
            priority=detail.priority,
            engagement_type=enum_value(detail.engagement_type),
            assessment_type=enum_value(detail.assessment_type),
            scope=detail.scope,
            asset_count=detail.counts.assets,
            manual_finding_count=detail.counts.manual_findings,
            automated_finding_count=detail.counts.automated_findings,
            requested_start_date=detail.requested_start_date,
            requested_end_date=detail.requested_end_date,
            scheduled_start_date=detail.scheduled_start_date,
            scheduled_end_date=detail.scheduled_end_date,
            target_date=detail.target_date,
            client_name=detail.client.full_name,
            assigned_pentester_name=(
                detail.assigned_pentester.full_name
                if detail.assigned_pentester
                else None
            ),
            service_delivery_name=(
                detail.service_delivery.full_name
                if detail.service_delivery
                else None
            ),
            report_status=(
                enum_value(report.status)
                if report
                else None
            ),
            report_available=(
                report is not None
                and report.status
                == ReportStatus.COMPLETED
            ),
            open_retest_count=open_retest_count,
            recent_findings=[
                AssistantEngagementFinding(
                    finding_id=finding.id,
                    title=finding.title,
                    severity=enum_value(finding.severity),
                    status=enum_value(finding.status),
                )
                for finding in detail.recent_findings
            ],
            href=engagement_href(
                user.role,
                detail.id,
            ),
        )


    @staticmethod
    def get_attention_reasons(
        summary: AssistantEngagementSummary,
        today: date,
    ) -> list[str]:
        reasons: list[str] = []
        horizon = today + timedelta(days=7)

        if(
            summary.status
            in {
                EngagementStatus.REQUESTED.value,
                EngagementStatus.SCOPING.value,
            }
            and summary.assigned_pentester_name is None
        ):
            reasons.append("No pentester is assigned")

        if(
            summary.status
            == EngagementStatus.SCHEDULED.value
            and summary.scheduled_start_date is not None
            and summary.scheduled_start_date <= horizon
        ):
            reasons.append("Scheduled to start within seven days")

        if(
            summary.status
            == EngagementStatus.IN_PROGRESS.value
            and summary.target_date is not None
            and summary.target_date <= horizon
        ):
            reasons.append("Target date is within seven days")

        if(
            summary.status
            == EngagementStatus.REVIEW.value
        ):
            reasons.append("Awaiting review")

        return reasons


    @staticmethod
    async def get_engagement_attention_queue(
        db: AsyncSession,
        user: User,
        limit: int = 10,
        today: date | None = None,
    ) -> list[AssistantEngagementSummary]:
        bounded_limit = max(1, min(limit, 20))
        selected_date = today or date.today()

        candidates = (
            await AssistantEngagementService.list_my_engagements(
                db,
                user=user,
                limit=20,
            )
        )

        results: list[AssistantEngagementSummary] = []

        for summary in candidates:
            reasons = (
                AssistantEngagementService.get_attention_reasons(
                    summary,
                    today=selected_date,
                )
            )

            if not reasons:
                continue

            results.append(summary.model_copy(
                update={
                    "attention_reasons": reasons,
                }
            ))

        return results[:bounded_limit]


    @staticmethod
    def build_evidence(
        summaries: list[AssistantEngagementSummary],
        intent: AssistantEngagementIntent,
        selected: bool,
    ) -> str:
        lines = [
            f"Engagement query intent: {intent.value}",
            (
                "A specific authorized engagement was selected."
                if selected
                else "Authorized engagement results:"
            ),
        ]

        if not summaries:
            lines.append(
                "No authorized engagements matched this query."
            )
            return "\n".join(lines)

        for summary in summaries:
            lines.extend(
                [
                    f"- Engagement ID: {summary.engagement_id}",
                    f"  Title: {summary.title}",
                    f"  Status: {summary.status}",
                    f"  Priority: {summary.priority}",
                    (
                        "  Engagement type: "
                        f"{summary.engagement_type}"
                    ),
                    (
                        "  Assessment type: "
                        f"{summary.assessment_type}"
                    ),
                    f"  Assets: {summary.asset_count}",
                    (
                        "  Requested start: "
                        f"{summary.requested_start_date}"
                    ),
                    (
                        "  Requested end: "
                        f"{summary.requested_end_date}"
                    ),
                    (
                        "  Scheduled start: "
                        f"{summary.scheduled_start_date}"
                    ),
                    (
                        "  Scheduled end: "
                        f"{summary.scheduled_end_date}"
                    ),
                    f"  Target date: {summary.target_date}",
                    (
                        "  Assigned pentester: "
                        f"{summary.assigned_pentester_name}"
                    ),
                    (
                        "  Service delivery: "
                        f"{summary.service_delivery_name}"
                    ),
                ]
            )

            if summary.scope is not None:
                lines.append(
                    f"  Scope: {summary.scope}"
                )

            if summary.manual_finding_count is not None:
                lines.append(
                    "  Manual findings: "
                    f"{summary.manual_finding_count}"
                )

            if summary.automated_finding_count is not None:
                lines.append(
                    "  Automated findings: "
                    f"{summary.automated_finding_count}"
                )

            if summary.report_available is not None:
                lines.append(
                    "  Report available: "
                    f"{summary.report_available}"
                )
                lines.append(
                    "  Report status: "
                    f"{summary.report_status}"
                )

            if summary.open_retest_count is not None:
                lines.append(
                    "  Open retests: "
                    f"{summary.open_retest_count}"
                )

            if summary.attention_reasons:
                lines.append(
                    "  Attention reasons: "
                    + "; ".join(summary.attention_reasons)
                )

            if summary.recent_findings:
                lines.append("  Recent findings:")

                lines.extend(
                    (
                        "    - "
                        f"{finding.title}; "
                        f"severity={finding.severity}; "
                        f"status={finding.status}; "
                        f"finding_id={finding.finding_id}"
                    )
                    for finding in summary.recent_findings
                )

        return "\n".join(lines)