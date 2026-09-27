import json
from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import Finding
from app.models.user import User
from app.repositories.finding_repository import FindingRepository
from app.schemas.assistant import (
    AssistantLink,
    AssistantQueryRequest,
    AssistantSource,
    AssistantSourceMetadata,
    AssistantSourceType,
)
from app.services.assistant_answer_validator import AssistantFindingEvidence
from app.services.engagement_service import EngagementService
from app.services.scan_service import ScanService


@dataclass(slots=True)
class FindingContextResult:
    evidence: str
    sources: list[AssistantSource]
    links: list[AssistantLink]
    grounding_evidence: tuple[
        AssistantFindingEvidence,
        ...,
    ] = ()
    authorized_entity_ids: tuple[UUID, ...] = ()
    allowed_links: tuple[str, ...] = ()


def display(value: object | None) -> str:
    if value is None:
        return "Not provided"

    if isinstance(value, Enum):
        return str(value.value)

    normalized = str(value).strip()
    return normalized or "Not provided"


def engagement_href(
        user_role: str,
        engagement_id: object,
) -> str:
    if user_role == "service_delivery":
        return f"/service-delivery/engagements/{engagement_id}"

    if user_role == "pentester":
        return (
            "/pentesting/console/my-engagements/"
            f"{engagement_id}/findings"
        )

    return f"/pentesting/engagement/{engagement_id}"


class AssistantContextService:
    @staticmethod
    async def try_scan_access(
        db: AsyncSession,
        user: User,
        finding: Finding,
    ) -> bool:
        if finding.scan_id is None:
            return False

        try:
            await ScanService.require_scan_access(
                db,
                scan_id=finding.scan_id,
                user_id=user.id,
            )

        except HTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                return False

            raise

        return True


    @staticmethod
    async def try_engagement_access(
        db: AsyncSession,
        user: User,
        finding: Finding,
    ) -> bool:
        if finding.engagement_id is None:
            return False

        try:
            await EngagementService.require_viewable_engagement(
                db,
                engagement_id=finding.engagement_id,
                user_id=user.id,
            )

        except HTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                return False

            raise

        return True


    @staticmethod
    def build_finding_evidence(
        finding: Finding,
        include_scan: bool,
        include_engagement: bool,
    ) -> str:
        scan = finding.scan if include_scan else None
        engagement = (
            finding.engagement
            if include_engagement
            else None
        )

        asset_identifier = None
        asset_type = None

        if include_scan and finding.asset is not None:
            asset_identifier = finding.asset.identifier
            asset_type = finding.asset.asset_type

        elif (
            include_engagement
            and finding.engagement_asset is not None
        ):
            asset_identifier = finding.engagement_asset.identifier
            asset_type = finding.engagement_asset.asset_type

        service = finding.service if include_scan else None

        structured_evidence = json.dumps(
            finding.evidence or {},
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )

        if len(structured_evidence) > 4000:
            structured_evidence = (
                structured_evidence[:4000]
                + "... [evidence truncated]"
            )

        evidence_files = ", ".join(
            evidence.file_name
            for evidence in finding.evidence_files
        ) or "None"

        lines = [
            f"Finding ID: {finding.id}",
            f"Title: {display(finding.title)}",
            f"Severity: {display(finding.severity)}",
            f"CVSS score: {display(finding.cvss_score)}",
            f"CVE: {display(finding.cve_id)}",
            f"Status: {display(finding.status)}",
            f"Verified: {'Yes' if finding.is_verified else 'No'}",
            f"Review status: {display(finding.review_status)}",
            f"Source: {display(finding.source)}",
            f"Scan domain: {display(scan.domain if scan else None)}",
            (
                "Engagement: "
                f"{display(engagement.title if engagement else None)}"
            ),
            f"Asset: {display(asset_identifier)}",
            f"Asset type: {display(asset_type)}",
            f"Service host: {display(service.host if service else None)}",
            f"Service port: {display(service.port if service else None)}",
            f"Protocol: {display(service.protocol if service else None)}",
            (
                "Service name: "
                f"{display(service.service_name if service else None)}"
            ),
            f"Product: {display(service.product if service else None)}",
            (
                "Product version: "
                f"{display(service.version if service else None)}"
            ),
            "",
            "Description:",
            display(finding.description),
            "",
            "Recorded recommendation:",
            display(finding.recommendation),
            "",
            "Review note:",
            display(finding.review_note),
            "",
            f"Evidence files: {evidence_files}",
            "",
            "Structured evidence:",
            structured_evidence,
        ]

        return "\n".join(lines)


    @staticmethod
    async def get_finding_context(
        db: AsyncSession,
        user: User,
        request: AssistantQueryRequest,
    ) -> FindingContextResult:
        finding_id = request.context.finding_id

        if finding_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Finding context is required.",
            )

        finding = await FindingRepository.get_with_context(
            db,
            finding_id=finding_id,
        )

        if finding is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Finding was not found.",
            )

        scan_authorized = False
        engagement_authorized = False

        if request.context.scan_id is not None:
            if finding.scan_id != request.context.scan_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Finding was not found.",
                )

            await ScanService.require_scan_access(
                db,
                scan_id=request.context.scan_id,
                user_id=user.id,
            )

            scan_authorized = True

        if request.context.engagement_id is not None:
            if finding.engagement_id != request.context.engagement_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Finding was not found.",
                )

            await EngagementService.require_viewable_engagement(
                db,
                engagement_id=request.context.engagement_id,
                user_id=user.id,
            )

            engagement_authorized = True

        if (
            request.context.scan_id is None
            and request.context.engagement_id is None
        ):
            engagement_authorized = (
                await AssistantContextService.try_engagement_access(
                    db,
                    user=user,
                    finding=finding,
                )
            )

            if not engagement_authorized:
                scan_authorized = (
                    await AssistantContextService.try_scan_access(
                        db,
                        user=user,
                        finding=finding,
                    )
                )

        if not scan_authorized and not engagement_authorized:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Finding was not found.",
            )

        evidence = AssistantContextService.build_finding_evidence(
            finding,
            include_scan=scan_authorized,
            include_engagement=engagement_authorized,
        )

        if scan_authorized and finding.scan_id is not None:
            href = (
                f"/phase2_scan/results/{finding.scan_id}/findings"
                f"?finding={finding.id}"
            )

        elif (
            engagement_authorized
            and finding.engagement_id is not None
        ):
            href = engagement_href(
                user.role,
                finding.engagement_id,
            )

        else:
            href = None

        asset_identifier = None

        if scan_authorized and finding.asset is not None:
            asset_identifier = finding.asset.identifier

        elif (
            engagement_authorized
            and finding.engagement_asset is not None
        ):
            asset_identifier = finding.engagement_asset.identifier

        service = (
            finding.service
            if scan_authorized
            else None
        )

        sources = [
            AssistantSource(
                source_type=AssistantSourceType.FINDING,
                source_id=str(finding.id),
                title=finding.title,
                severity=display(finding.severity),
                href=href,
                metadata=AssistantSourceMetadata(
                    cve_id=finding.cve_id,
                    cvss_score=(
                        float(finding.cvss_score)
                        if finding.cvss_score is not None
                        else None
                    ),
                    status=display(finding.status),
                    is_verified=finding.is_verified,
                    domain=(
                        str(finding.scan.domain)
                        if (
                            scan_authorized
                            and finding.scan is not None
                        )
                        else None
                    ),
                    asset_identifier=asset_identifier,
                    service_host=(
                        service.host
                        if service is not None
                        else None
                    ),
                    service_port=(
                        service.port
                        if service is not None
                        else None
                    ),
                    service_protocol=(
                        service.protocol
                        if service is not None
                        else None
                    ),
                    selection_reasons=[
                        "Selected finding",
                    ],
                ),
            )
        ]

        links = (
            [
                AssistantLink(
                    label="Open finding",
                    href=href,
                )
            ]
            if href is not None
            else []
        )

        authorized_entity_ids = [finding.id]

        if scan_authorized and finding.scan_id is not None:
            authorized_entity_ids.append(finding.scan_id)

        if (
            engagement_authorized
            and finding.engagement_id is not None
        ):
            authorized_entity_ids.append(finding.engagement_id)

        grounding_evidence = (
            AssistantFindingEvidence(
                finding_id=finding.id,
                severity=display(finding.severity),
                cvss_score=(
                    float(finding.cvss_score)
                    if finding.cvss_score is not None
                    else None
                ),
                cves=(
                    (finding.cve_id,)
                    if finding.cve_id
                    else ()
                ),
            ),
        )

        return FindingContextResult(
            evidence=evidence,
            sources=sources,
            links=links,
            grounding_evidence=grounding_evidence,
            authorized_entity_ids=tuple(authorized_entity_ids),
            allowed_links=(
                (href,)
                if href is not None
                else ()
            ),
        )
