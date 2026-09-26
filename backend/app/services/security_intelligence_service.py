from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from ipaddress import ip_address
from typing import Literal, TypeAlias, cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import FindingStatus
from app.models.finding import Finding
from app.models.scan import Scan
from app.repositories.finding_repository import FindingRepository
from app.repositories.scan_repo import ScanRepository
from app.schemas.assistant import AssistantQueryRequest
from app.schemas.security_intelligence import (
    SecurityComparisonFinding,
    SecurityExactFinding,
    SecurityExactLookupResult,
    SecurityPortfolioDomainRisk,
    SecurityPortfolioFinding,
    SecurityPortfolioResult,
    SecurityPriorityFinding,
    SecurityRecurringIssue,
    SecurityScanComparisonResult,
    SecuritySeverityCounts,
)
from app.services.rag.document_builder import build_finding_text
from app.services.security_query_router import SecurityQueryRouter

FindingIdentity: TypeAlias = tuple[
    str,
    str,
    str,
    str,
    str,
    str,
    str,
    str,
]


class SecurityIntelligenceService:

    SEVERITY_WEIGHTS = {
        "critical": 25,
        "high": 15,
        "medium": 5,
        "low": 1,
        "info": 0,
    }

    SEVERITY_RANKS = {
        "critical": 5,
        "high": 4,
        "medium": 3,
        "low": 2,
        "info": 1,
    }


    @staticmethod
    def build_priority_reasons(
        finding: Finding,
    ) -> list[str]:
        severity = (
            finding.severity.value
            if hasattr(finding.severity, "value")
            else str(finding.severity)
        )

        reasons = [
            f"{severity.replace('_', ' ').title()} severity"
        ]

        if finding.cvss_score is not None:
            reasons.append(
                f"CVSS {float(finding.cvss_score):.1f}"
            )

        if finding.is_verified:
            reasons.append("Verified finding")

        if finding.status == FindingStatus.OPEN:
            reasons.append("Open and not yet remediated")

        elif finding.status == FindingStatus.IN_PROGRESS:
            reasons.append("Remediation is currently in progress")

        return reasons


    @classmethod
    async def prioritize_scan_findings(
        cls,
        db: AsyncSession,
        scan_id: UUID,
        limit: int = 5,
    ) -> list[SecurityPriorityFinding]:
        findings = (
            await FindingRepository.list_prioritized_for_scan(
                db,
                scan_id=scan_id,
                limit=limit,
            )
        )

        results: list[SecurityPriorityFinding] = []

        for priority, finding in enumerate(
            findings,
            start=1,
        ):
            severity = (
                finding.severity.value
                if hasattr(finding.severity, "value")
                else str(finding.severity)
            )

            status = (
                finding.status.value
                if hasattr(finding.status, "value")
                else str(finding.status)
            )

            results.append(
                SecurityPriorityFinding(
                    finding_id=finding.id,
                    priority=priority,
                    title=finding.title,
                    severity=severity,
                    cvss_score=(
                        float(finding.cvss_score)
                        if finding.cvss_score is not None
                        else None
                    ),
                    cve_id=finding.cve_id,
                    status=status,
                    is_verified=finding.is_verified,
                    priority_reasons=(
                        cls.build_priority_reasons(
                            finding
                        )
                    ),
                    content=build_finding_text(
                        finding
                    ),
                )
            )

        return results


    @classmethod
    async def lookup_exact_scan_findings(
        cls,
        db: AsyncSession,
        scan_id: UUID,
        request: AssistantQueryRequest,
        limit: int = 5,
    ) -> SecurityExactLookupResult:
        finding_id = (
            SecurityQueryRouter.extract_finding_id(
                request
            )
        )

        cve_id = SecurityQueryRouter.extract_cve_id(
            request
        )

        identifier_type: Literal[
            "finding_id",
            "cve",
        ]
        identifier_value: str
        match_reason: str

        if finding_id is not None:
            identifier_type = "finding_id"
            identifier_value = str(finding_id)
            match_reason = "Exact finding ID match"

        elif cve_id is not None:
            identifier_type = "cve"
            identifier_value = cve_id
            match_reason = f"CVE match: {cve_id}"

        else:
            return SecurityExactLookupResult(
                identifier_type=None,
                identifier_value=None,
            )

        findings = await FindingRepository.list_exact_for_scan(
            db,
            scan_id=scan_id,
            finding_id=finding_id,
            cve_id=(
                None
                if finding_id is not None
                else cve_id
            ),
            limit=limit,
        )

        results: list[SecurityExactFinding] = []

        for finding in findings:
            severity = (
                finding.severity.value
                if hasattr(finding.severity, "value")
                else str(finding.severity)
            )

            status = (
                finding.status.value
                if hasattr(finding.status, "value")
                else str(finding.status)
            )

            results.append(
                SecurityExactFinding(
                    finding_id=finding.id,
                    title=finding.title,
                    severity=severity,
                    cvss_score=(
                        float(finding.cvss_score)
                        if finding.cvss_score is not None
                        else None
                    ),
                    cve_id=finding.cve_id,
                    status=status,
                    is_verified=finding.is_verified,
                    match_reason=match_reason,
                    content=build_finding_text(finding),
                )
            )

        return SecurityExactLookupResult(
            identifier_type=identifier_type,
            identifier_value=identifier_value,
            findings=results,
        )


    @staticmethod
    def normalize_identity_value(
        value: object | None,
    ) -> str:
        if value is None:
            return ""

        return " ".join(
            str(value).strip().casefold().split()
        )


    @staticmethod
    def is_ip_address(
        value: object | None,
    ) -> bool:
        if value is None:
            return False

        try:
            ip_address(str(value).strip())

        except ValueError:
            return False

        return True


    @classmethod
    def finding_identity(
        cls,
        finding: Finding,
    ) -> FindingIdentity:
        asset = finding.asset
        service = finding.service
        scan = finding.scan

        asset_identifier = (
            asset.identifier
            if asset is not None
            else None
        )

        service_host = (
            service.host
            if service is not None
            else None
        )

        scan_domain = (
            scan.domain
            if scan is not None
            else None
        )

        if (
            scan_domain is not None
            and cls.is_ip_address(asset_identifier)
        ):
            asset_identifier = scan_domain

        if (
            scan_domain is not None
            and cls.is_ip_address(service_host)
        ):
            service_host = scan_domain

        return (
            cls.normalize_identity_value(finding.source),
            cls.normalize_identity_value(finding.cve_id),
            cls.normalize_identity_value(finding.title),
            cls.normalize_identity_value(asset_identifier),
            cls.normalize_identity_value(
                asset.asset_type
                if asset is not None
                else None
            ),
            cls.normalize_identity_value(service_host),
            cls.normalize_identity_value(
                service.port
                if service is not None
                else None
            ),
            cls.normalize_identity_value(
                service.protocol
                if service is not None
                else None
            ),
        )


    @classmethod
    def classify_scan_findings(
        cls,
        *,
        current_findings: Sequence[Finding],
        baseline_findings: Sequence[Finding],
    ) -> tuple[
        list[Finding],
        list[tuple[Finding, Finding]],
        list[Finding],
    ]:
        current_by_identity: dict[
            FindingIdentity,
            list[Finding],
        ] = defaultdict(list)

        baseline_by_identity: dict[
            FindingIdentity,
            list[Finding],
        ] = defaultdict(list)

        for finding in current_findings:
            current_by_identity[
                cls.finding_identity(finding)
            ].append(finding)

        for finding in baseline_findings:
            baseline_by_identity[
                cls.finding_identity(finding)
            ].append(finding)

        new_findings: list[Finding] = []
        persistent_findings: list[
            tuple[Finding, Finding]
        ] = []

        no_longer_detected: list[Finding] = []

        identities = (
            set(current_by_identity)
            | set(baseline_by_identity)
        )

        for identity in sorted(identities):
            current_group = sorted(
                current_by_identity.get(identity, []),
                key=lambda finding: str(finding.id),
            )
            baseline_group = sorted(
                baseline_by_identity.get(identity, []),
                key=lambda finding: str(finding.id),
            )

            persistent_count = min(
                len(current_group),
                len(baseline_group),
            )

            persistent_findings.extend(
                zip(
                    current_group[:persistent_count],
                    baseline_group[:persistent_count],
                    strict=True,
                )
            )

            new_findings.extend(
                current_group[persistent_count:]
            )

            no_longer_detected.extend(
                baseline_group[persistent_count:]
            )

        return (
            new_findings,
            persistent_findings,
            no_longer_detected,
        )


    @staticmethod
    def build_comparison_finding(
        finding: Finding,
        change: Literal[
            "new",
            "persistent",
            "no_longer_detected",
        ],
        previous_finding_id: UUID | None = None,
    ) -> SecurityComparisonFinding:
        severity = (
            finding.severity.value
            if hasattr(finding.severity, "value")
            else str(finding.severity)
        )

        status = (
            finding.status.value
            if hasattr(finding.status, "value")
            else str(finding.status)
        )

        asset = finding.asset
        service = finding.service

        assert finding.scan_id is not None

        return SecurityComparisonFinding(
            finding_id=finding.id,
            scan_id=finding.scan_id,
            previous_finding_id=previous_finding_id,
            change=change,
            title=finding.title,
            severity=severity,
            status=status,
            source=finding.source,
            cvss_score=(
                float(finding.cvss_score)
                if finding.cvss_score is not None
                else None
            ),
            cve_id=finding.cve_id,
            is_verified=finding.is_verified,
            asset_identifier=(
                asset.identifier
                if asset is not None
                else None
            ),
            asset_type=(
                asset.asset_type
                if asset is not None
                else None
            ),
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
            description=finding.description,
            recommendation=finding.recommendation,
        )


    @classmethod
    async def compare_with_previous_scan(
        cls,
        db: AsyncSession,
        current_scan: Scan,
        user_id: UUID,
    ) -> SecurityScanComparisonResult:

        current_scan_id = cast(
            UUID,
            current_scan.id,
        )

        current_scan_created_at = cast(
            datetime,
            current_scan.created_at,
        )

        baseline_scan = (
            await ScanRepository.find_previous_comparable_scan(
                db,
                current_scan=current_scan,
                user_id=user_id,
            )
        )

        if baseline_scan is None:
            return SecurityScanComparisonResult(
                comparison_available=False,
                current_scan_id=current_scan_id,
                current_scan_created_at=current_scan_created_at,
            )

        baseline_scan_id = cast(
            UUID,
            baseline_scan.id,
        )

        baseline_scan_created_at = cast(
            datetime,
            baseline_scan.created_at,
        )

        current_findings = (
            await FindingRepository.list_for_scan_comparison(
                db,
                scan_id=current_scan_id,
            )
        )

        baseline_findings = (
            await FindingRepository.list_for_scan_comparison(
                db,
                scan_id=baseline_scan_id,
            )
        )

        (
            new_findings,
            persistent_findings,
            no_longer_detected,
        ) = cls.classify_scan_findings(
            current_findings=current_findings,
            baseline_findings=baseline_findings,
        )

        return SecurityScanComparisonResult(
            comparison_available=True,
            current_scan_id=current_scan_id,
            current_scan_created_at=current_scan_created_at,
            baseline_scan_id=baseline_scan_id,
            baseline_scan_created_at=baseline_scan_created_at,
            new_findings=[
                cls.build_comparison_finding(
                    finding,
                    change="new",
                )
                for finding in new_findings
            ],
            persistent_findings=[
                cls.build_comparison_finding(
                    current_finding,
                    change="persistent",
                    previous_finding_id=baseline_finding.id
                )
                for (
                    current_finding,
                    baseline_finding,
                ) in persistent_findings
            ],
            no_longer_detected=[
                cls.build_comparison_finding(
                    finding,
                    change="no_longer_detected",
                )
                for finding in no_longer_detected
            ],
        )


    @staticmethod
    def enum_text(value: object) -> str:
        raw_value = (
            value.value
            if hasattr(value, "value")
            else value
        )

        return str(raw_value).strip().casefold()


    @classmethod
    def select_latest_scans_by_domain(
        cls,
        scans: Sequence[Scan],
    ) -> list[Scan]:
        ordered = sorted(
            scans,
            key=lambda scan: (
                cast(
                    datetime,
                    scan.completed_at or scan.created_at,
                ),
                cast(datetime, scan.created_at),
                str(scan.id),
            ),
            reverse=True,
        )

        latest_by_domain: dict[str, Scan] = {}

        for scan in ordered:
            normalized_domain = (
                cls.normalize_identity_value(scan.domain)
            )

            latest_by_domain.setdefault(
                normalized_domain,
                scan,
            )

        return [
            latest_by_domain[domain]
            for domain in sorted(latest_by_domain)
        ]


    @classmethod
    def portfolio_finding_sort_key(
        cls,
        finding: Finding,
    ) -> tuple[int, float, int, str, str]:
        severity = cls.enum_text(finding.severity)

        return (
            -cls.SEVERITY_RANKS.get(severity, 0),
            -(
                float(finding.cvss_score)
                if finding.cvss_score is not None
                else -1.0
            ),
            -int(finding.is_verified),
            finding.title.casefold(),
            str(finding.id),
        )


    @classmethod
    def build_portfolio_finding(
        cls,
        finding: Finding,
        scan: Scan,
    ) -> SecurityPortfolioFinding:
        scan_id = cast(UUID, scan.id)
        asset = finding.asset
        service = finding.service

        return SecurityPortfolioFinding(
            finding_id=finding.id,
            scan_id=scan_id,
            domain=str(scan.domain),
            title=finding.title,
            severity=cls.enum_text(finding.severity),
            status=cls.enum_text(finding.status),
            source=finding.source,
            cvss_score=(
                float(finding.cvss_score)
                if finding.cvss_score is not None
                else None
            ),
            cve_id=finding.cve_id,
            is_verified=finding.is_verified,
            asset_identifier=(
                asset.identifier
                if asset is not None
                else None
            ),
            service_port=(
                service.port
                if service is not None
                else None
            ),
        )


    @classmethod
    def build_recurring_issues(
        cls,
        scans_by_id: dict[UUID, Scan],
        findings: Sequence[Finding],
    ) -> list[SecurityRecurringIssue]:
        grouped: dict[
            tuple[Literal["cve", "title"], str],
            list[Finding],
        ] = defaultdict(list)

        for finding in findings:
            if (
                finding.scan_id is not None
                and finding.scan_id in scans_by_id
            ):
                grouped[
                    cls.portfolio_issue_identity(finding)
                ].append(finding)

        recurring: list[SecurityRecurringIssue] = []

        for (
            identity_type,
            identifier,
        ), issue_findings in grouped.items():
            domains = {
                cls.normalize_identity_value(
                    scans_by_id[
                        cast(UUID, finding.scan_id)
                    ].domain
                ): str(
                    scans_by_id[
                        cast(UUID, finding.scan_id)
                    ].domain
                )
                for finding in issue_findings
            }

            if len(domains) < 2:
                continue

            ordered_findings = sorted(
                issue_findings,
                key=cls.portfolio_finding_sort_key,
            )

            representative_by_domain: dict[str, Finding] = {}

            for finding in ordered_findings:
                scan = scans_by_id[
                    cast(UUID, finding.scan_id)
                ]

                normalized_domain = (
                    cls.normalize_identity_value(scan.domain)
                )

                representative_by_domain.setdefault(
                    normalized_domain,
                    finding,
                )

            representative_findings = [
                cls.build_portfolio_finding(
                    finding,
                    scan=scans_by_id[
                        cast(UUID, finding.scan_id)
                    ],
                )
                for finding in representative_by_domain.values()
            ]

            highest_severity = cls.enum_text(
                ordered_findings[0].severity
            )

            cve_ids = {
                finding.cve_id.strip().upper()
                for finding in issue_findings
                if (
                    finding.cve_id is not None
                    and finding.cve_id.strip()
                )
            }

            recurring.append(
                SecurityRecurringIssue(
                    identity_type=identity_type,
                    identifier=identifier,
                    title=ordered_findings[0].title,
                    cve_id=(
                        sorted(cve_ids)[0]
                        if cve_ids
                        else None
                    ),
                    sources=sorted(
                        {
                            finding.source
                            for finding in issue_findings
                        },
                        key=str.casefold,
                    ),
                    highest_severity=highest_severity,
                    affected_domain_count=len(domains),
                    affected_domains=[
                        domains[key]
                        for key in sorted(domains)
                    ],
                    occurrence_count=len(issue_findings),
                    representative_findings=representative_findings[:5],
                )
            )

        recurring.sort(
            key=lambda issue: (
                -issue.affected_domain_count,
                -cls.SEVERITY_RANKS.get(
                    issue.highest_severity,
                    0,
                ),
                -issue.occurrence_count,
                issue.identifier.casefold(),
            )
        )

        return recurring


    @classmethod
    def build_portfolio_result(
        cls,
        scans: Sequence[Scan],
        findings: Sequence[Finding],
    ) -> SecurityPortfolioResult:
        if not scans:
            return SecurityPortfolioResult(
                portfolio_available=False,
            )

        scans_by_id = {
            cast(UUID, scan.id): scan
            for scan in scans
        }

        findings_by_scan: dict[
            UUID,
            list[Finding],
        ] = defaultdict(list)

        for finding in findings:
            if (
                finding.scan_id is not None
                and finding.scan_id in scans_by_id
            ):
                findings_by_scan[
                    finding.scan_id
                ].append(finding)

        total_counts = {
            severity: 0
            for severity in cls.SEVERITY_WEIGHTS
        }

        ranked_domains: list[
            tuple[int, SecurityPortfolioDomainRisk]
        ] = []

        for scan in scans:
            scan_id = cast(UUID, scan.id)
            scan_findings = findings_by_scan.get(
                scan_id,
                [],
            )

            severity_counts = {
                severity: 0
                for severity in cls.SEVERITY_WEIGHTS
            }

            for finding in scan_findings:
                severity = cls.enum_text(finding.severity)

                if severity in severity_counts:
                    severity_counts[severity] += 1
                    total_counts[severity] += 1

            raw_risk_points = sum(
                severity_counts[severity] * weight
                for severity, weight
                in cls.SEVERITY_WEIGHTS.items()
            )

            ordered_findings = sorted(
                scan_findings,
                key=cls.portfolio_finding_sort_key,
            )

            scan_type = cls.enum_text(scan.scan_type)

            domain_result = SecurityPortfolioDomainRisk(
                rank=1,
                domain=str(scan.domain),
                scan_id=scan_id,
                scan_type=scan_type,
                scan_created_at=cast(datetime, scan.created_at),
                risk_score=min(100, raw_risk_points),
                active_finding_count=len(scan_findings),
                severity_counts=SecuritySeverityCounts(
                    **severity_counts
                ),
                top_findings=[
                    cls.build_portfolio_finding(
                        finding,
                        scan=scan,
                    )
                    for finding in ordered_findings[:5]
                ],
            )

            ranked_domains.append(
                (
                    raw_risk_points,
                    domain_result,
                )
            )

        ranked_domains.sort(
            key=lambda item: (
                -item[0],
                -item[1].severity_counts.critical,
                -item[1].severity_counts.high,
                -item[1].severity_counts.medium,
                item[1].domain.casefold(),
                str(item[1].scan_id),
            )
        )

        domains = [
            result.model_copy(
                update={"rank": rank}
            )
            for rank, (_, result) in enumerate(
                ranked_domains,
                start=1,
            )
        ]

        selected_findings = [
            finding
            for scan_findings
            in findings_by_scan.values()
            for finding in scan_findings
        ]

        recurring_issues = cls.build_recurring_issues(
            scans_by_id=scans_by_id,
            findings=selected_findings,
        )

        return SecurityPortfolioResult(
            portfolio_available=True,
            domain_count=len(domains),
            active_finding_count=len(selected_findings),
            severity_counts=SecuritySeverityCounts(
                **total_counts
            ),
            domains=domains,
            recurring_issues=recurring_issues,
        )


    @classmethod
    async def analyze_portfolio(
        cls,
        db: AsyncSession,
        user_id: UUID,
    ) -> SecurityPortfolioResult:
        completed_scans = (
            await ScanRepository.list_completed_for_portfolio(
                db,
                user_id=user_id,
            )
        )

        latest_scans = (
            cls.select_latest_scans_by_domain(completed_scans)
        )

        if not latest_scans:
            return SecurityPortfolioResult(
                portfolio_available=False,
            )

        scan_ids = [
            cast(UUID, scan.id)
            for scan in latest_scans
        ]

        findings = (
            await FindingRepository.list_active_for_scans(
                db,
                scan_ids=scan_ids,
            )
        )

        return cls.build_portfolio_result(
            scans=latest_scans,
            findings=findings,
        )


    @classmethod
    def portfolio_issue_identity(
        cls,
        finding: Finding,
    ) -> tuple[Literal["cve", "title"], str]:
        normalized_cve = (
            cls.normalize_identity_value(finding.cve_id)
        )

        if normalized_cve:
            return (
                "cve",
                normalized_cve.upper(),
            )

        normalized_title = (
            cls.normalize_identity_value(finding.title)
        )

        normalized_source = (
            cls.normalize_identity_value(finding.source)
        )

        return (
            "title",
            f"{normalized_source}:{normalized_title}",
        )


    @staticmethod
    def select_portfolio_evidence(
        result: SecurityPortfolioResult,
        limit: int = 10,
    ) -> list[SecurityPortfolioFinding]:
        selected: dict[
            UUID, 
            SecurityPortfolioFinding,
        ] = {}

        def add(
                finding: SecurityPortfolioFinding,
        ) -> None:
            if len(selected) >= limit:
                return

            selected.setdefault(
                finding.finding_id,
                finding,
            )

        for domain in result.domains[:5]:
            if domain.top_findings:
                add(domain.top_findings[0])

        for issue in result.recurring_issues[:5]:
            for finding in issue.representative_findings:
                add(finding)

        for domain in result.domains[:5]:
            for finding in domain.top_findings:
                add(finding)

        return list(selected.values())