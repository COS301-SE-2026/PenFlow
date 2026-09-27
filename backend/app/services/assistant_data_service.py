from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import DomainVerificationStatus
from app.models.user import User
from app.repositories.report_repository import (
    list_completed_scan_reports_for_user,
)
from app.repositories.scan_repo import ScanRepository
from app.schemas.assistant import (
    AssistantLink,
    AssistantQueryRequest,
    AssistantSource,
    AssistantSourceType,
)
from app.schemas.domain import (
    DomainSortField,
)
from app.schemas.domain import (
    SortOrder as DomainSortOrder,
)
from app.services.assistant_conversation import build_routing_text
from app.services.assistant_engagement_service import (
    AssistantEngagementIntent,
    AssistantEngagementService,
)
from app.services.domain_service import DomainService
from app.services.notification_service import NotificationService
from app.services.scan_schedule_service import ScanScheduleService


class AssistantDataIntent(str, Enum):
    NEXT_SCAN = "next_scan"
    RECENT_SCANS = "recent_scans"
    DOMAINS = "domains"
    NOTIFICATIONS = "notifications"
    ENGAGEMENTS = "engagements"
    REPORTS = "reports"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class AssistantDataResult:
    intent: AssistantDataIntent
    evidence: str
    sources: list[AssistantSource]
    links: list[AssistantLink]
    engagement_intent: AssistantEngagementIntent | None = None


def enum_value(value: object) -> str:
    if isinstance(value, Enum):
        return str(value.value)

    return str(value)


def format_datetime(
        value: datetime,
        timezone_name: str | None,
) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    try:
        selected_timezone = ZoneInfo(timezone_name or "UTC")

    except ZoneInfoNotFoundError:
        selected_timezone = ZoneInfo("UTC")

    return value.astimezone(selected_timezone).strftime(
        "%Y-%m-%d %H:%M %Z"
    )


def engagement_list_href(role: str) -> str:
    if role == "service_delivery":
        return "/service-delivery/engagements"

    if role in {"pentester", "admin"}:
        return "/pentesting/console/my-engagements"

    return "/pentesting/engagement"


class AssistantDataService:
    SCHEDULE_PHRASES = (
        "next scan",
        "scheduled scan",
        "scan schedule",
        "upcoming scan",
    )

    RECENT_SCAN_PHRASES = (
        "latest scan",
        "last scan",
        "recent scan",
        "most recent scan",
        "scans have i run",
        "my scans",
    )

    DOMAIN_PHRASES = (
        "my domain",
        "my domains",
        "unverified domain",
        "domain status",
        "how many domains",
        "domains do i have",
    )

    NOTIFICATION_PHRASES = (
        "notification",
        "notifications",
        "unread notification",
        "needs my attention",
    )

    ENGAGEMENT_PHRASES = (
        "my engagement",
        "my engagements",
        "this engagement",
        "engagement status",
        "status of my engagement",
        "engagements require attention",
        "engagements need attention",
        "engagements need scheduling",
        "engagements awaiting review",
        "engagements assigned to me",
        "what should i work on next",
        "my pentest",
        "my retest",
        "engagement report",
        "which engagements",
        "engagements are",
        "no pentester",
        "who is assigned",
        "open retest",
    )

    REPORT_PHRASES = (
        "my report",
        "my reports",
        "available report",
        "available reports",
        "completed report",
        "reports are available",
    )


    @classmethod
    def classify_intent(
        cls,
        question: str,
    ) -> AssistantDataIntent:
        normalized = question.casefold()

        intent_phrases = (
            (
                AssistantDataIntent.NEXT_SCAN,
                cls.SCHEDULE_PHRASES,
            ),
            (
                AssistantDataIntent.RECENT_SCANS,
                cls.RECENT_SCAN_PHRASES,
            ),
            (
                AssistantDataIntent.DOMAINS,
                cls.DOMAIN_PHRASES,
            ),
            (
                AssistantDataIntent.NOTIFICATIONS,
                cls.NOTIFICATION_PHRASES,
            ),
            (
                AssistantDataIntent.ENGAGEMENTS,
                cls.ENGAGEMENT_PHRASES,
            ),
            (
                AssistantDataIntent.REPORTS,
                cls.REPORT_PHRASES,
            ),
        )

        for intent, phrases in intent_phrases:
            if any(phrase in normalized for phrase in phrases):
                return intent

        return AssistantDataIntent.UNKNOWN


    @staticmethod
    async def collect_next_scan(
        db: AsyncSession,
        user: User,
    ) -> AssistantDataResult:
        schedules = await ScanScheduleService.list_schedules(
            db,
            user_id=user.id,
        )

        active_schedules = [
            schedule
            for schedule in schedules
            if schedule.is_active
        ]

        if not active_schedules:
            evidence = "The user has no active scheduled scans."
            sources: list[AssistantSource] = []

        else:
            schedule = min(
                active_schedules,
                key=lambda item: item.next_run_at,
            )

            domain_name = schedule.verified_domain.domain

            evidence = (
                "Next active scheduled scan:\n"
                f"- Domain: {domain_name}\n"
                f"- Frequency: {enum_value(schedule.frequency)}\n"
                f"- Next run: "
                f"{format_datetime(schedule.next_run_at, schedule.timezone)}\n"
                f"- Schedule timezone: {schedule.timezone}\n"
                f"- Schedule ID: {schedule.id}"
            )

            sources = [
                AssistantSource(
                    source_type=AssistantSourceType.USER_DATA,
                    source_id=str(schedule.id),
                    title=f"Scheduled scan for {domain_name}",
                    href="/scheduled-scans",
                )
            ]

        return AssistantDataResult(
            intent=AssistantDataIntent.NEXT_SCAN,
            evidence=evidence,
            sources=sources,
            links=[
                AssistantLink(
                    label="View scheduled scans",
                    href="/scheduled-scans",
                )
            ],
        )


    @staticmethod
    async def collect_recent_scans(
        db: AsyncSession,
        user: User,
        timezone_name: str | None,
    ) -> AssistantDataResult:
        scans = await ScanRepository.list_scans(
            db,
            user_id=user.id,
            limit=5,
            offset=0,
        )

        if not scans:
            evidence = "The user has not run any scans."
        else:
            lines = ["The user's five most recent scans are:"]

            for scan in scans:
                lines.append(
                    (
                        f"- {scan['domain']}; "
                        f"status={enum_value(scan['status'])}; "
                        f"type={enum_value(scan['scan_type'])}; "
                        f"created="
                        f"{format_datetime(scan['created_at'], timezone_name)}; "
                        f"findings={scan['total_findings']}; "
                        f"critical={scan['critical_count']}; "
                        f"high={scan['high_count']}; "
                        f"scan_id={scan['id']}"
                    )
                )

            evidence = "\n".join(lines)

        sources = [
            AssistantSource(
                source_type=AssistantSourceType.USER_DATA,
                source_id=str(scan["id"]),
                title=f"Scan of {scan['domain']}",
                href=f"/phase2_scan/results/{scan['id']}",
            )
            for scan in scans
        ]

        return AssistantDataResult(
            intent=AssistantDataIntent.RECENT_SCANS,
            evidence=evidence,
            sources=sources,
            links=[
                AssistantLink(
                    label="Open scan history",
                    href="/history",
                )
            ],
        )


    @staticmethod
    async def collect_domains(
        db: AsyncSession,
        user: User,
    ) -> AssistantDataResult:
        domain_list = await DomainService.list_domains(
            db,
            user_id=user.id,
            verification_status=None,
            search=None,
            sort=DomainSortField.CREATED_AT,
            order=DomainSortOrder.DESC,
            limit=100,
            offset=0,
        )

        unverified = [
            domain
            for domain in domain_list.items
            if domain.status != DomainVerificationStatus.VERIFIED
        ]

        lines = [
            "Authorized domain summary:",
            f"- Total: {domain_list.counts.all}",
            f"- Verified: {domain_list.counts.verified}",
            f"- Pending: {domain_list.counts.pending}",
            f"- Failed: {domain_list.counts.failed}",
            f"- Expired: {domain_list.counts.expired}",     
        ]

        if unverified:
            lines.append("Domains that are not currently verified:")

            lines.extend(
                (
                    f"- {domain.domain}; "
                    f"status={enum_value(domain.status)}; "
                    f"domain_id={domain.id}"
                )
                for domain in unverified[:10]
            )

        else:
            lines.append(
                "No unverified domains were present in the retrieved records."
            )

        sources = [
            AssistantSource(
                source_type=AssistantSourceType.USER_DATA,
                source_id=str(domain.id),
                title=domain.domain,
                href="/domains",
            )
            for domain in domain_list.items[:10]
        ]

        return AssistantDataResult(
            intent=AssistantDataIntent.DOMAINS,
            evidence="\n".join(lines),
            sources=sources,
            links=[
                AssistantLink(
                    label="Manage domains",
                    href="/domains",
                )
            ],
        )


    @staticmethod
    async def collect_notifications(
        db: AsyncSession,
        user: User,
        timezone_name: str | None,
    ) -> AssistantDataResult:
        notifications = await NotificationService.list_notifications(
            db,
            user_id=user.id,
            unread_only=True,
            limit=5,
            offset=0,
        )

        lines = [
            f"Unread notification count: {notifications.unread_count}"
        ]

        for notification in notifications.items:
            lines.append(
                (
                    f"- {notification.title}; "
                    f"message={notification.message}; "
                    f"created="
                    f"{format_datetime(notification.created_at, timezone_name)}; "
                    f"notification_id={notification.id}"
                )
            )

        if not notifications.items:
            lines.append("The user has no unread notifications.")

        sources = [
            AssistantSource(
                source_type=AssistantSourceType.USER_DATA,
                source_id=str(notification.id),
                title=notification.title,
                href="/",
            )
            for notification in notifications.items
        ]

        return AssistantDataResult(
            intent=AssistantDataIntent.NOTIFICATIONS,
            evidence="\n".join(lines),
            sources=sources,
            links=[
                AssistantLink(
                    label="Open PenFlow",
                    href="/",
                )
            ],
        )


    @staticmethod
    async def collect_reports(
        db: AsyncSession,
        user: User,
        timezone_name: str | None,
    ) -> AssistantDataResult:
        reports = await list_completed_scan_reports_for_user(
            db,
            user_id=user.id,
            limit=5,
        )

        if not reports:
            evidence = (
                "No completed scan reports are currently available "
                "to this user."
            )

        else:
            lines = ["The user's latest completed scan reports are:"]

            for report, domain in reports:
                generated = (
                    format_datetime(report.generated_at, timezone_name)
                    if report.generated_at
                    else "generation time unavailable"
                )

                lines.append(
                    (
                        f"- {domain}; generated={generated}; "
                        f"scan_id={report.scan_id}; "
                        f"report_id={report.id}"
                    )
                )

            evidence = "\n".join(lines)

        sources = [
            AssistantSource(
                source_type=AssistantSourceType.USER_DATA,
                source_id=str(report.id),
                title=f"Security report for {domain}",
                href=f"/report/{report.scan_id}",
            )
            for report, domain in reports
        ]

        return AssistantDataResult(
            intent=AssistantDataIntent.REPORTS,
            evidence=evidence,
            sources=sources,
            links=[
                AssistantLink(
                    label="Open scan history",
                    href="/history",
                )
            ],
        )


    @staticmethod
    async def collect_engagement_question(
        db: AsyncSession,
        user: User,
        request: AssistantQueryRequest,
    ) -> AssistantDataResult:
        routing_text = build_routing_text(request)

        engagement_intent = (
            AssistantEngagementService.classify_intent(routing_text)
        )
        selected = (
            request.context.engagement_id is not None
        )

        detail_only_intents = {
            AssistantEngagementIntent.FINDINGS,
            AssistantEngagementIntent.REPORT,
            AssistantEngagementIntent.RETESTS,
        }

        if selected:
            engagement_id = (request.context.engagement_id)

            if engagement_id is None:
                raise RuntimeError(
                    "Selected engagement ID is missing."
                )

            summaries = [
                await (
                    AssistantEngagementService.get_engagement_summary(
                        db,
                        user=user,
                        engagement_id=engagement_id,
                    )
                )
            ]

        elif engagement_intent in detail_only_intents:
            return AssistantDataResult(
                intent=AssistantDataIntent.ENGAGEMENTS,
                engagement_intent=engagement_intent,
                evidence=(
                    "No engagement was selected. Open an "
                    "authorized engagement before asking about "
                    "its findings, report, or retests."
                ),
                sources=[],
                links=[
                    AssistantLink(
                        label="View engagements",
                        href=engagement_list_href(user.role),
                    )
                ],
            )

        elif (
            engagement_intent
            == AssistantEngagementIntent.ATTENTION
        ):
            summaries = await AssistantEngagementService.get_engagement_attention_queue(
                db,
                user=user,
                limit=10,
            )

        else:
            engagement_status = (
                AssistantEngagementService.extract_status(
                    routing_text
                )
                if engagement_intent
                == AssistantEngagementIntent.STATUS
                else None
            )

            summaries = await AssistantEngagementService.list_my_engagements(
                db,
                user=user,
                engagement_status=engagement_status,
                limit=10,
            )

        return AssistantDataResult(
            intent=AssistantDataIntent.ENGAGEMENTS,
            engagement_intent=engagement_intent,
            evidence=(
                AssistantEngagementService.build_evidence(
                    summaries,
                    intent=engagement_intent,
                    selected=selected,
                )
            ),
            sources=[
                AssistantSource(
                    source_type=AssistantSourceType.USER_DATA,
                    source_id=str(summary.engagement_id),
                    title=summary.title,
                    href=summary.href,
                )
                for summary in summaries
            ],
            links=[
                AssistantLink(
                    label="View engagements",
                    href=engagement_list_href(user.role),
                )
            ],
        )
            


    @classmethod
    async def collect(
        cls,
        db: AsyncSession,
        user: User,
        request: AssistantQueryRequest,
    ) -> AssistantDataResult:
        intent = cls.classify_intent(
            build_routing_text(request)
        )

        if (
            request.context.engagement_id is not None
            or intent == AssistantDataIntent.ENGAGEMENTS
        ):
            return await cls.collect_engagement_question(
                db,
                user=user,
                request=request,
            )

        if intent == AssistantDataIntent.NEXT_SCAN:
            return await cls.collect_next_scan(
                db,
                user=user,
            )

        if intent == AssistantDataIntent.RECENT_SCANS:
            return await cls.collect_recent_scans(
                db,
                user=user,
                timezone_name=request.context.timezone,
            )

        if intent == AssistantDataIntent.DOMAINS:
            return await cls.collect_domains(
                db,
                user=user,
            )

        if intent == AssistantDataIntent.NOTIFICATIONS:
            return await cls.collect_notifications(
                db,
                user=user,
                timezone_name=request.context.timezone,
            )

        if intent == AssistantDataIntent.REPORTS:
            return await cls.collect_reports(
                db,
                user=user,
                timezone_name=request.context.timezone,
            )

        return AssistantDataResult(
            intent=AssistantDataIntent.UNKNOWN,
            evidence=(
                "The requested live-data category could not be identified. "
                "No account records were retrieved."
            ),
            sources=[],
            links=[],
        )