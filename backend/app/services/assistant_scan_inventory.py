import re
from enum import Enum
from typing import Literal, cast

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.scan_source import ScanSource
from app.models.service import Service
from app.models.user import User
from app.schemas.assistant import (
    AssistantAnswerState,
    AssistantCapability,
    AssistantLink,
    AssistantQueryRequest,
    AssistantQueryResponse,
)
from app.services.assistant_scan_details import (
    ANALYSIS_TERMS,
    service_ports,
)
from app.services.scan_service import ScanService

Category = Literal["assets", "services", "sources"]
LIMIT = 20


def inventory_categories(question: str) -> tuple[Category, ...]:
    text = question.casefold().strip()

    if not re.match(r"^(?:what|which|list|show|how many)\b", text):
        return ()

    if ANALYSIS_TERMS.search(text) or re.search(
        r"\b(?:configure|fix|remediate)\b",
        text,
    ):
        return ()

    categories: list[Category] = []

    for category, pattern in (
        ("assets", r"\bassets?\b"),
        ("services", r"\bservices?\b(?!\s+delivery)"),
        ("sources", r"\b(?:sources?|workers?)\b"),
    ):
        if re.search(pattern, text):
            categories.append(cast(Category, category))

    return tuple(categories)


def display(value: object) -> str:
    if isinstance(value, Enum):
        value = value.value

    text = " ".join(str(value).split())[:255]
    return re.sub(r"([\\`*_{}\[\]()<>#!|])", r"\\\1", text)


async def answer_scan_inventory(
    db: AsyncSession,
    *,
    user: User,
    request: AssistantQueryRequest,
    categories: tuple[Category, ...],
) -> AssistantQueryResponse:
    scan_id = request.context.scan_id

    if scan_id is None:
        return AssistantQueryResponse(
            question=request.question,
            answer=(
                "Open the relevant scan and ask again "
                "so I can read its inventory."
            ),
            answer_state=AssistantAnswerState.INSUFFICIENT_EVIDENCE,
            capability=AssistantCapability.USER_DATA,
            links=[
                AssistantLink(
                    label="Open scans",
                    href="/phase2_scan",
                )
            ],
        )

    scan = await ScanService.require_scan_access(
        db,
        scan_id,
        user.id,
    )

    ports = (
        service_ports(request.question)
        if "services" in categories
        else ()
    )

    if ports is None:
        return AssistantQueryResponse(
            question=request.question,
            answer="Specify service ports between 0 and 65535.",
            answer_state=AssistantAnswerState.INSUFFICIENT_EVIDENCE,
            capability=AssistantCapability.USER_DATA,
        )

    sections: list[str] = []
    links: list[AssistantLink] = []
    base = f"/phase2_scan/results/{scan_id}"

    try:
        if "assets" in categories:
            total = int(
                await db.scalar(
                    select(func.count())
                    .select_from(Asset)
                    .where(Asset.scan_id == scan_id)
                )
                or 0
            )

            assets = (
                (
                    await db.execute(
                        select(Asset)
                        .where(Asset.scan_id == scan_id)
                        .order_by(
                            Asset.asset_type,
                            Asset.identifier,
                            Asset.id,
                        )
                        .limit(LIMIT)
                    )
                )
                .scalars()
                .all()
            )

            lines = [
                f"## Assets\n{total} asset records currently recorded."
            ]

            lines.extend(
                f"- {display(asset.identifier)}"
                f" — {display(asset.asset_type)}"
                for asset in assets
            )

            if total > len(assets):
                lines.append(
                    f"Showing {len(assets)} of {total}; "
                    "open Assets for the full list."
                )

            sections.append("\n".join(lines))
            links.append(
                AssistantLink(
                    label="View assets",
                    href=f"{base}/assets",
                )
            )

        if "services" in categories:
            service_filters = [Service.scan_id == scan_id]

            if ports:
                service_filters.append(Service.port.in_(ports))

            total = int(
                await db.scalar(
                    select(func.count())
                    .select_from(Service)
                    .where(*service_filters)
                )
                or 0
            )

            services = (
                (
                    await db.execute(
                        select(Service)
                        .where(*service_filters)
                        .order_by(
                            Service.host,
                            Service.port,
                            Service.protocol,
                            Service.id,
                        )
                        .limit(LIMIT)
                    )
                )
                .scalars()
                .all()
            )

            lines = [
                f"## Services\n{total} matching service records currently recorded."
            ]

            if ports:
                lines.append(
                    "Port filter: " + ", ".join(map(str, ports))
                )

            lines.extend(
                f"- {display(service.host)}:"
                f"{service.port}/{display(service.protocol)}"
                f" — {display(service.service_name or 'Unnamed service')}"
                f"; state: {display(service.state)}"
                for service in services
            )

            if total > len(services):
                lines.append(
                    f"Showing {len(services)} of {total}; "
                    "open Services for the full list."
                )

            sections.append("\n".join(lines))
            links.append(
                AssistantLink(
                    label="View services",
                    href=f"{base}/services",
                )
            )

        if "sources" in categories:
            total = int(
                await db.scalar(
                    select(func.count())
                    .select_from(ScanSource)
                    .where(ScanSource.scan_id == scan_id)
                )
                or 0
            )

            sources = (
                (
                    await db.execute(
                        select(ScanSource)
                        .where(ScanSource.scan_id == scan_id)
                        .order_by(
                            ScanSource.source_name,
                            ScanSource.id,
                        )
                        .limit(LIMIT)
                    )
                )
                .scalars()
                .all()
            )

            lines = [
                f"## Source statuses\n"
                f"{total} source records currently recorded."
            ]

            lines.extend(
                f"- {display(source.source_name)}"
                f" — {display(source.status)}"
                for source in sources
            )

            if total > len(sources):
                lines.append(
                    f"Showing {len(sources)} of {total}; "
                    "open Activity for the full list."
                )

            sections.append("\n".join(lines))
            links.append(
                AssistantLink(
                    label="View activity",
                    href=f"{base}/activity",
                )
            )

    except SQLAlchemyError:
        return AssistantQueryResponse(
            question=request.question,
            answer=(
                "I could not retrieve this scan's inventory. "
                "This does not mean it is empty. Try again later."
            ),
            answer_state=AssistantAnswerState.INSUFFICIENT_EVIDENCE,
            capability=AssistantCapability.USER_DATA,
        )

    note = (
        f"Scan status: {display(scan.status)}. "
        "Inventory is a live snapshot and may change."
    )

    return AssistantQueryResponse(
        question=request.question,
        answer="\n\n".join([note, *sections]),
        capability=AssistantCapability.USER_DATA,
        links=links,
    )