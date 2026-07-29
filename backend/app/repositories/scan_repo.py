import builtins
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import String, case, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as psg_insert

from app.models.asset import Asset
from app.models.base import ScanStatus, Severity, ScanSourceStatus, FindingStatus
from app.models.detected_technology import DetectedTechnology
from app.models.finding import Finding
from app.models.report import Report
from app.models.scan import Scan
from app.models.scan_source import ScanSource
from app.models.service import Service

logger = logging.getLogger(__name__)

# This could easily change
PASSIVE_SCAN_SOURCES = (
    "dns",
    "urlscan",
    "wappalyzer",
    "crt.sh",
    "shodan",
    "hibp",
)

ACTIVE_SCAN_SOURCES = (
    "dns",
    "crt.sh",
    "shodan",
    "hibp",
    "target_resolution",
    "nmap",
    "http_security",
    "tls",
    "fingerprint",
    "cve",
)

SCAN_SOURCES_BY_TYPE: dict[str, tuple[str, ...]] = {
    "passive_ctem": PASSIVE_SCAN_SOURCES,
    "active_vulnerability": ACTIVE_SCAN_SOURCES,
}

class ScanRepository:
    @staticmethod
    async def create_scan(
        db: AsyncSession,
        domain: str,
        scan_type: str = "passive_ctem",
        email: str | None = None,
        user_id: UUID | None = None,
        verified_domain_id: UUID | None = None,
    ) -> Scan:
        """Creates a new pending scan record in the database."""
        try:
            new_scan = Scan(
                domain=domain,
                scan_type=scan_type,
                email=email,
                user_id=user_id,
                verified_domain_id=verified_domain_id,
            )
            db.add(new_scan)
            await db.commit()
            await db.refresh(new_scan)
            return new_scan
        except SQLAlchemyError:
            await db.rollback()
            logger.exception("Failed to create scan for domain %s", domain)
            raise

    @staticmethod
    async def get_scan_by_id(db: AsyncSession, scan_id: UUID) -> Scan | None:
        """Retrieves a scan and its associated assets/findings."""
        query = select(Scan).where(Scan.id == scan_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_scans(
        db: AsyncSession, 
        user_id: UUID,
        status: ScanStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        query = (
            select(
                Scan,
                func.count(Finding.id).label("total_findings"),
                func.sum(case((Finding.severity == Severity.CRITICAL, 1), else_=0)).label(
                    "critical_count"
                ),
                func.sum(case((Finding.severity == Severity.HIGH, 1), else_=0)).label("high_count"),
                func.sum(case((Finding.severity == Severity.MEDIUM, 1), else_=0)).label(
                    "medium_count"
                ),
                func.sum(case((Finding.severity == Severity.LOW, 1), else_=0)).label("low_count"),
            )
            .outerjoin(Finding, Finding.scan_id == Scan.id)
            .where(Scan.user_id == user_id)
            .group_by(Scan.id)
            .order_by(Scan.created_at.desc())
        )

        if status:
            query = query.where(Scan.status == status)

        query = query.limit(limit).offset(offset)
        rows = (await db.execute(query)).all()
        return [
            {
                "id": row.Scan.id,
                "domain": row.Scan.domain,
                "created_at": row.Scan.created_at,
                "status": row.Scan.status,
                "scan_type": row.Scan.scan_type,
                "progress": row.Scan.progress,
                "total_findings": int(row.total_findings or 0),
                "critical_count": int(row.critical_count or 0),
                "high_count": int(row.high_count or 0),
                "medium_count": int(row.medium_count or 0),
                "low_count": int(row.low_count or 0),
            }
            for row in rows
        ]

    @staticmethod
    async def mark_scan_failed(
        db: AsyncSession, scan_id: UUID, error_message: str, is_partial: bool = False
    ) -> Scan:  # noqa: E501
        """
        Update scan's status to failed or partial and logs the exact error, for frontend display
        """
        scan = await ScanRepository.get_scan_by_id(db, scan_id)
        if not scan:
            raise ValueError(f"Scan {scan_id} not found.")

        scan.status = ScanStatus.PARTIAL if is_partial else ScanStatus.FAILED
        scan.error_message = error_message

        await db.commit()
        await db.refresh(scan)
        return scan

    @staticmethod
    async def save_source_result(
        db: AsyncSession,
        scan_id: UUID,
        source_name: str,
        payload: dict[str, Any],
    ) -> Scan:

        scan = await ScanRepository.get_scan_by_id(db, scan_id)

        if not scan:
            raise ValueError(f"Scan {scan_id} not found.")

        try:
            source_status = payload["status"]

            query = (
                psg_insert(ScanSource).values(
                    scan_id=scan.id,
                    source_name=source_name,
                    status=ScanSourceStatus(source_status),
                    raw_result=payload.get("raw_result"),
                    error_message=payload.get("error_message"),
                ).on_conflict_do_update(
                    index_elements = [
                        "scan_id",
                        "source_name",
                    ],
                    set_ = {
                        "status": ScanSourceStatus(source_status),
                        "raw_result": payload.get("raw_result"),
                        "error_message": payload.get("error_message"),
                    },
                )
            )

            await db.execute(query)

            asset_cache: dict[str, Asset] = {}

            for asset_data in payload.get("assets", []):
                identifier = asset_data.get("identifier")
                asset_type = asset_data.get("asset_type", "unknown")

                if not identifier:
                    continue

                query = (
                    psg_insert(Asset).values(
                        scan_id=scan.id,
                        identifier=identifier,
                        asset_type=asset_type,
                        asset_metadata=asset_data.get("asset_metadata", {}),
                    ).on_conflict_do_nothing(
                        index_elements = [
                            "scan_id",
                            "identifier",
                            "asset_type",
                        ]
                    )
                )

                await db.execute(query)

                asset_result = await db.execute(
                    select(Asset).where(
                        Asset.scan_id == scan.id,
                        Asset.identifier == identifier,
                        Asset.asset_type == asset_type,
                    )
                )
                asset = asset_result.scalar_one_or_none()

                asset_cache[identifier] = asset

            service_cache: dict[tuple[str, int, str], Service] = {}

            for service_data in payload.get("services", []):
                host = service_data.get("host")
                port = service_data.get("port")
                protocol = service_data.get("protocol")

                if not host or port is None or not protocol:
                    continue

                asset = asset_cache.get(host)

                if asset is None:
                    asset_query = select(Asset).where(
                        Asset.scan_id == scan.id,
                        Asset.identifier == host,
                    )

                    asset_result = await db.execute(asset_query)
                    asset = asset_result.scalar_one_or_none()


                query = (
                    psg_insert(Service).values(
                        scan_id=scan.id,
                        asset_id=asset.id if asset else None,
                        host=host,
                        port=port,
                        protocol=protocol,
                        service_name=service_data.get("service_name"),
                        product=service_data.get("product"),
                        version=service_data.get("version"),
                        banner=service_data.get("banner"),
                        state=service_data.get("state", "open"),
                        tls_enabled=service_data.get("tls_enabled", False),
                    ).on_conflict_do_nothing(
                        index_elements = [
                            "scan_id",
                            "host",
                            "port",
                            "protocol",
                        ]
                    )
                )

                await db.execute(query)

                service_result = await db.execute(
                    select(Service).where(
                        Service.scan_id == scan.id,
                        Service.host == host,
                        Service.port == port,
                        Service.protocol == protocol,
                    )
                )
                service = service_result.scalar_one_or_none()

                if asset and service.asset_id is None:
                    service.asset_id = asset.id

                if service_data.get("service_name"):
                    service.service_name = service_data["service_name"]

                if service_data.get("product"):
                    service.product = service_data["product"]

                if service_data.get("version"):
                    service.version = service_data["version"]

                if service_data.get("banner"):
                    service.banner = service_data["banner"]

                if service_data.get("state"):
                    service.state = service_data["state"]

                if service_data.get("tls_enabled"):
                    service.tls_enabled = True

                service_cache[host, port, protocol] = service

            for technology_data in payload.get("technologies", []):
                product = technology_data.get("product")
                technology_type = technology_data.get("technology_type")

                if not product or not technology_type:
                    continue

                host = technology_data.get("host")
                port = technology_data.get("port")
                protocol = technology_data.get("protocol")

                asset = None
                service = None

                if host:
                    asset = asset_cache.get(host)

                    if asset is None:
                        asset_result = await db.execute(
                            select(Asset).where(
                                Asset.scan_id == scan.id,
                                Asset.identifier == host,
                            )
                        )

                        asset = asset_result.scalar_one_or_none()

                if host and port is not None and protocol:
                    service = service_cache.get(
                        (host, port, protocol)
                    )

                    if service is None:
                        service_result = await db.execute(
                            select(Service).where(
                                Service.scan_id == scan.id,
                                Service.host == host,
                                Service.port == port,
                                Service.protocol == protocol,
                            )
                        )

                        service = service_result.scalar_one_or_none()

                asset_id = asset.id if asset else None
                service_id = service.id if service else None

                technology_query = select(DetectedTechnology).where(
                    DetectedTechnology.scan_id == scan.id,
                    DetectedTechnology.product == product,
                    DetectedTechnology.technology_type == technology_type,
                    DetectedTechnology.version == technology_data.get("version"),
                    DetectedTechnology.asset_id == asset_id,
                    DetectedTechnology.service_id == service_id,
                )

                technology_result = await db.execute(technology_query)

                technology = technology_result.scalar_one_or_none()

                if technology is None:
                    technology = DetectedTechnology(
                        scan_id = scan.id,
                        asset_id = asset.id if asset else None,
                        service_id = service.id if service else None,
                        technology_type = technology_type,
                        product = product,
                        version = technology_data.get("version"),
                        confidence = technology_data.get("confidence"),
                        detection_source = technology_data.get("detection_source", source_name),
                        evidence = technology_data.get("evidence", {})
                    )

                    db.add(technology)

                else:
                    if asset and technology.asset_id is None:
                        technology.asset_id = asset.id

                    if service and technology.service_id is None:
                        technology.service_id = service.id

                    if technology_data.get("confidence") is not None:
                        technology.confidence = technology_data["confidence"]

                    technology.evidence = technology_data.get("evidence") or technology.evidence

            for finding_data in payload.get("findings", []):
                host = finding_data.get("host")
                port = finding_data.get("port")
                protocol = finding_data.get("protocol")

                asset = None
                service = None

                if host:
                    asset = asset_cache.get(host)

                    if asset is None:
                        asset_result = await db.execute(
                            select(Asset).where(
                                Asset.scan_id == scan.id,
                                Asset.identifier == host,
                            )
                        )

                        asset = asset_result.scalar_one_or_none()

                if host and port is not None and protocol:
                    service = service_cache.get(
                        (host, port, protocol)
                    )

                    if service is None:
                        service_result = await db.execute(
                            select(Service).where(
                                Service.scan_id == scan.id,
                                Service.host == host,
                                Service.port == port,
                                Service.protocol == protocol,
                            )
                        )

                        service = service_result.scalar_one_or_none()

                finding = Finding(
                    scan_id = scan.id,
                    asset_id = asset.id if asset else service.asset_id if service else None,
                    service_id = service.id if service else None,
                    source = finding_data.get("source", source_name),
                    status = FindingStatus(
                        finding_data.get("status", "open")
                    ),
                    cvss_score = finding_data.get("cvss_score"),
                    cve_id = finding_data.get("cve_id"),
                    severity = Severity(
                        finding_data.get("severity", "info").lower()
                    ),
                    title = finding_data.get("title", "Untitled finding"),
                    description = finding_data.get("description"),
                    recommendation = finding_data.get("recommendation"),
                    evidence = finding_data.get("evidence", {}),
                )

                db.add(finding)

            await db.flush()

            expected_sources = SCAN_SOURCES_BY_TYPE[scan.scan_type.value]

            source_status_results = await db.execute(
                select(ScanSource.source_name, ScanSource.status).where(
                    ScanSource.scan_id == scan.id, ScanSource.source_name.in_(expected_sources)
                )
            )

            source_statuses = source_status_results.all()
            total_sources = len(expected_sources)

            finished_statuses = [
                ScanSourceStatus.COMPLETED,
                ScanSourceStatus.FAILED,
                ScanSourceStatus.SKIPPED,
                ScanSourceStatus.PARTIAL,
            ]

            finished_count = sum(1 for _, status in source_statuses if status in finished_statuses)

            progress = int((finished_count / total_sources) * 100)
            scan.progress = builtins.min(progress, 100)

            if finished_count == total_sources:
                failed_sources = [
                    source_name
                    for source_name, status in source_statuses
                    if status != ScanSourceStatus.COMPLETED
                ]

                if len(failed_sources) == 0:
                    scan.status = ScanStatus.COMPLETED
                    scan.error_message = None

                elif len(failed_sources) == total_sources:
                    scan.status = ScanStatus.FAILED
                    scan.error_message = "All Scan Sources Failed"

                else:
                    scan.status = ScanStatus.PARTIAL
                    scan.error_message = f"Some Scan Sources Failed: {', '.join(failed_sources)}"
            else:
                scan.status = ScanStatus.RUNNING

            await db.commit()
            await db.refresh(scan)
            return scan

        except SQLAlchemyError:
            await db.rollback()
            logger.exception("Failed to save scan source result for scan %s", scan_id)
            raise

    @staticmethod
    async def get_scan_status(
        db: AsyncSession, scan_id: UUID, user_id: UUID | None
    ) -> dict[str, Any] | None:
        scan = await ScanRepository.get_scan_by_id(db, scan_id)

        if not scan:
            return None

        if scan.user_id is not None and scan.user_id != user_id:
            return None

        scan_type = (
            scan.scan_type.value if hasattr(scan.scan_type, "value") else str(scan.scan_type)
        )

        expected_sources = SCAN_SOURCES_BY_TYPE.get(scan_type)
        if expected_sources is None:
            raise ValueError(f"Unsupported scan type: {scan_type}")

        source_results = await db.execute(
            select(ScanSource).where(
                ScanSource.scan_id == scan_id, ScanSource.source_name.in_(expected_sources)
            )
        )

        sources = source_results.scalars().all()

        source_names = {source.source_name: source for source in sources}

        report_result = await db.execute(select(Report).where(Report.scan_id == scan_id))
        report = report_result.scalar_one_or_none()

        return {
            "scan_id": str(scan.id),
            "domain": scan.domain,
            "created_at": scan.created_at,
            "scan_type": scan_type,
            "status": scan.status.value,
            "progress": scan.progress,
            "sources": [
                {
                    "source_name": source,
                    "status": (
                        source_names[source].status.value
                        if source in source_names
                        else ScanSourceStatus.PENDING.value
                    ),
                    "error_message": (
                        source_names[source].error_message if source in source_names else None
                    ),
                }
                for source in expected_sources
            ],
            "report_status": {
                "status": report.status.value,
                "pdf_path": report.pdf_path,
            }
            if report
            else None,
        }

    @staticmethod
    async def update_scan_status(db: AsyncSession, scan_id: UUID, status: ScanStatus) -> None:
        scan = await ScanRepository.get_scan_by_id(db, scan_id)
        if scan:
            scan.status = status
            await db.commit()

    @staticmethod
    async def get_scan_metrics(db: AsyncSession, scan_id: UUID) -> dict[str, Any] | None:
        scan = await ScanRepository.get_scan_by_id(db, scan_id)
        if not scan:
            return None

        findings_stmt = (
            select(Finding.severity, func.count(Finding.id))
            .where(Finding.scan_id == scan_id)
            .group_by(Finding.severity)
        )
        f_rows = (await db.execute(findings_stmt)).all()
        findings_breakdown = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
            "total": 0,
        }
        for sev, count in f_rows:
            key = sev.value.lower() if hasattr(sev, "value") else str(sev).lower()
            if key in findings_breakdown:
                findings_breakdown[key] = count
                findings_breakdown["total"] += count

        assets_stmt = (
            select(Asset.asset_type, func.count(Asset.id))
            .where(Asset.scan_id == scan_id)
            .group_by(Asset.asset_type)
        )
        a_rows = (await db.execute(assets_stmt)).all()
        assets_breakdown = {"total": 0}
        for a_type, count in a_rows:
            assets_breakdown[a_type] = count
            assets_breakdown["total"] += count

        services_stmt = select(func.count(Service.id)).where(Service.scan_id == scan_id)
        total_services = await db.scalar(services_stmt) or 0

        tech_stmt = select(func.count(DetectedTechnology.id)).where(
            DetectedTechnology.scan_id == scan_id
        )
        total_tech = await db.scalar(tech_stmt) or 0

        weighted_score = (
            (findings_breakdown["critical"] * 25)
            + (findings_breakdown["high"] * 15)
            + (findings_breakdown["medium"] * 5)
            + (findings_breakdown["low"] * 1)
        )
        risk_score = builtins.min(100, weighted_score)

        return {
            "risk_score": risk_score,
            "risk_level": "HIGH RISK"
            if risk_score >= 70
            else ("MEDIUM RISK" if risk_score >= 40 else "LOW RISK"),
            "findings": findings_breakdown,
            "assets": assets_breakdown,
            "services": {"total": total_services},
            "technologies": {"total": total_tech},
        }

    @staticmethod
    async def get_findings_by_scan(
        db: AsyncSession,
        scan_id: UUID,
        severity: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        query = (
            select(Finding, Asset.identifier.label("asset_name"))
            .outerjoin(Asset, Finding.asset_id == Asset.id)
            .where(Finding.scan_id == scan_id)
        )

        if severity:
            query = query.where(Finding.severity == Severity(severity.lower()))

        query = query.order_by(Finding.created_at.desc())
        query = query.limit(limit).offset(offset)

        rows = (await db.execute(query)).all()
        return [
            {
                "id": str(row.Finding.id),
                "title": row.Finding.title,
                "cve_id": row.Finding.cve_id,
                "severity": row.Finding.severity.value,
                "cvss_score": float(row.Finding.cvss_score) if row.Finding.cvss_score else None,
                "source": row.Finding.source,
                "asset_identifier": row.asset_name,
                "description": row.Finding.description,
                "recommendation": row.Finding.recommendation,
            }
            for row in rows
        ]

    @staticmethod
    async def get_assets_by_scan(
        db: AsyncSession, scan_id: UUID, limit: int = 10, offset: int = 0
    ) -> list[dict[str, Any]]:
        query = (
            select(Asset, func.count(Finding.id).label("findings_count"))
            .outerjoin(Finding, Finding.asset_id == Asset.id)
            .where(Asset.scan_id == scan_id)
            .group_by(Asset.id)
            .order_by(func.count(Finding.id).desc())
            .limit(limit)
            .offset(offset)
        )

        rows = (await db.execute(query)).all()
        return [
            {
                "id": str(row.Asset.id),
                "identifier": row.Asset.identifier,
                "asset_type": row.Asset.asset_type,
                "findings_count": row.findings_count,
            }
            for row in rows
        ]

    @staticmethod
    async def get_domain_risk_history(db: AsyncSession, scan_id: UUID) -> list[dict[str, Any]]:
        scan = await ScanRepository.get_scan_by_id(db, scan_id)
        if not scan:
            return []

        query = (
            select(Scan.id, Scan.created_at)
            .where(Scan.domain == scan.domain, Scan.status == ScanStatus.COMPLETED)
            .order_by(Scan.created_at.asc())
            .limit(10)
        )
        historical_scans = (await db.execute(query)).all()

        history = []
        for h_scan_id, h_created_at in historical_scans:
            metrics = await ScanRepository.get_scan_metrics(db, h_scan_id)
            if metrics:
                history.append(
                    {
                        "date": h_created_at.strftime("%b %d"),
                        "risk_score": metrics["risk_score"],
                        "total_findings": metrics["findings"]["total"],
                    }
                )
        return history

    @staticmethod
    async def get_findings_page(
        db: AsyncSession,
        scan_id: UUID,
        severity: str | None = None,
        search: str | None = None,
        sort_by: str = "severity",
        limit: int = 12,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """
        Retrieves paginated, filtered and sorted findings for the Findings tab,
        along with overall severity counts for the top cards.
        """

        counts_stmt = (
            select(Finding.severity, func.count(Finding.id))
            .where(Finding.scan_id == scan_id)
            .group_by(Finding.severity)
        )
        c_rows = (await db.execute(counts_stmt)).all()

        counts = {"critical": 0, "high": 0, "medium": 0, "low_info": 0, "total": 0}
        for sev, count in c_rows:
            key = sev.value.lower() if hasattr(sev, "value") else str(sev).lower()
            if key in counts:
                counts[key] = count
            elif key in ["low", "info"]:
                counts["low_info"] += count
            counts["total"] += count

        query = (
            select(
                Finding, Asset.identifier.label("asset_name"), Asset.asset_type.label("asset_type")
            )
            .outerjoin(Asset, Finding.asset_id == Asset.id)
            .where(Finding.scan_id == scan_id)
        )

        if severity and severity.lower() != "all":
            if severity.lower() == "low_info":
                query = query.where(Finding.severity.in_([Severity.LOW, Severity.INFO]))
            else:
                query = query.where(Finding.severity == Severity(severity.lower()))

        if search:
            search_term = f"%{search.strip()}%"
            query = query.where(
                (Finding.title.ilike(search_term))
                | (Finding.description.ilike(search_term))
                | (Asset.identifier.ilike(search_term))
            )

        if sort_by == "severity":
            severity_case = case(
                (Finding.severity == Severity.CRITICAL, 5),
                (Finding.severity == Severity.HIGH, 4),
                (Finding.severity == Severity.MEDIUM, 3),
                (Finding.severity == Severity.LOW, 2),
                else_=1,
            ).label("sev_rank")
            query = query.order_by(severity_case.desc(), Finding.cvss_score.desc().nulls_last())
        elif sort_by == "cvss":
            query = query.order_by(Finding.cvss_score.desc().nulls_last())
        else:
            query = query.order_by(Finding.created_at.desc())

        query = query.limit(limit).offset(offset)
        rows = (await db.execute(query)).all()

        items = []
        for row in rows:
            f = row.Finding
            items.append(
                {
                    "id": str(f.id),
                    "title": f.title,
                    "severity": f.severity.value,
                    "cvss_score": float(f.cvss_score) if f.cvss_score else None,
                    "cve_id": f.cve_id,
                    "source": f.source,
                    "status": f.status.value if hasattr(f.status, "value") else str(f.status),
                    "description": f.description,
                    "recommendation": f.recommendation,
                    "asset_identifier": row.asset_name,
                    "asset_type": row.asset_type,
                    "evidence": f.evidence,
                    "created_at": f.created_at,
                }
            )

        return items, counts

    @staticmethod
    async def get_services_page(
        db: AsyncSession,
        scan_id: UUID,
        protocol: str | None = None,
        search: str | None = None,
        sort_by: str = "open",
        limit: int = 15,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """
        Retrieves paginated, filtered and sorted services for the services tab
        along with summary counter metrics.
        """

        all_services_stmt = select(Service).where(Service.scan_id == scan_id)
        all_rows = (await db.execute(all_services_stmt)).scalars().all()

        counts = {"total": len(all_rows), "tcp": 0, "udp": 0, "open": 0, "filtered": 0}
        for s in all_rows:
            proto = (s.protocol or "").upper()
            if proto == "TCP":
                counts["tcp"] += 1
            elif proto == "UDP":
                counts["udp"] += 1

            state = (s.state or "").lower()
            if state == "filtered":
                counts["filtered"] += 1
            elif state == "open":
                counts["open"] += 1

        query = select(Service).where(Service.scan_id == scan_id)

        if protocol and protocol.upper() != "ALL":
            query = query.where(func.upper(Service.protocol) == protocol.upper())

        if search:
            search_term = f"%{search.strip()}%"
            query = query.where(
                (Service.service_name.ilike(search_term))
                | (Service.product.ilike(search_term))
                | (Service.host.ilike(search_term))
                | (func.cast(Service.port, String).ilike(search_term))
            )

        if sort_by == "port":
            query = query.order_by(Service.port.asc())
        else:
            query = query.order_by(Service.created_at.desc())

        query = query.limit(limit).offset(offset)
        rows = (await db.execute(query)).scalars().all()

        severity_rank = {"info": 1, "low": 2, "medium": 3, "high": 4, "critical": 5}

        items = []
        for s in rows:
            asset_count_stmt = select(func.count(Asset.id)).where(
                Asset.scan_id == scan_id, Asset.identifier == s.host
            )
            a_count = await db.scalar(asset_count_stmt) or 1

            finding_stmt = select(Finding.severity).where(
                Finding.scan_id == scan_id, Finding.asset_id == s.asset_id
            )
            finding_rows = (await db.execute(finding_stmt)).scalars().all()

            highest_sev = "Low"
            if finding_rows:
                top_sev = max(
                    finding_rows,
                    key=lambda sev: severity_rank.get(
                        sev.value.lower() if hasattr(sev, "value") else str(sev).lower(), 0
                    ),
                )
                highest_sev = (
                    top_sev.value.capitalize()
                    if hasattr(top_sev, "value")
                    else str(top_sev).capitalize()
                )

            items.append(
                {
                    "id": str(s.id),
                    "service_name": s.service_name or s.product or "Unknown Service",
                    "host": s.host,
                    "port": s.port,
                    "protocol": s.protocol.upper(),
                    "product": s.product,
                    "version": s.version,
                    "state": s.state.capitalize() if hasattr(s, "state") and s.state else "Open",
                    "risk_level": highest_sev,
                    "asset_count": a_count,
                    "banner": s.banner,
                    "created_at": s.created_at,
                }
            )

        return items, counts

    @staticmethod
    async def get_assets_page(
        db: AsyncSession,
        scan_id: UUID,
        asset_type: str | None = None,
        severity: str | None = None,
        search: str | None = None,
        sort_by: str = "risk",
        limit: int = 15,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """
        Retrieves paginated, filtered and sorted assets for the Assets tab,
        along with category counter metrics for the top cards.
        """
        all_assets_stmt = select(Asset).where(Asset.scan_id == scan_id)
        all_rows = (await db.execute(all_assets_stmt)).scalars().all()

        counts = {
            "total": len(all_rows),
            "domains": 0,
            "ips": 0,
            "subdomains": 0,
            "urls": 0,
            "other": 0,
        }
        for a in all_rows:
            t = (a.asset_type or "").lower()
            if "domain" in t and "sub" not in t:
                counts["domains"] += 1
            elif "ip" in t:
                counts["ips"] += 1
            elif "sub" in t:
                counts["subdomains"] += 1
            elif "url" in t:
                counts["urls"] += 1
            else:
                counts["other"] += 1

        query = select(Asset).where(Asset.scan_id == scan_id)

        if asset_type and asset_type.lower() != "all":
            query = query.where(func.lower(Asset.asset_type) == asset_type.lower())

        if search:
            search_term = f"%{search.strip()}%"
            query = query.where(Asset.identifier.ilike(search_term))

        rows = (await db.execute(query)).scalars().all()

        severity_rank = {"info": 1, "low": 2, "medium": 3, "high": 4, "critical": 5}
        items = []

        for a in rows:
            findings_stmt = select(Finding.severity).where(Finding.asset_id == a.id)
            f_rows = (await db.execute(findings_stmt)).scalars().all()

            f_count = len(f_rows)
            highest_sev = "Low"
            if f_rows:
                top_sev = max(
                    f_rows,
                    key=lambda sev: severity_rank.get(
                        sev.value.lower() if hasattr(sev, "value") else str(sev).lower(), 0
                    ),
                )
                highest_sev = (
                    top_sev.value.capitalize()
                    if hasattr(top_sev, "value")
                    else str(top_sev).capitalize()
                )

            if severity and severity.lower() != "all":
                if highest_sev.lower() != severity.lower():
                    continue

            meta: dict[str, Any] = a.asset_metadata or {}
            ip_addr = meta.get("ip_address") or meta.get("ip") or "203.0.113.24"

            items.append(
                {
                    "id": str(a.id),
                    "identifier": a.identifier,
                    "asset_type": a.asset_type.capitalize(),
                    "ip_address": ip_addr,
                    "severity": highest_sev,
                    "findings_count": f_count,
                    "status": "Active",
                    "created_at": a.created_at,
                }
            )

        if sort_by == "risk":
            items.sort(key=lambda x: severity_rank.get(x["severity"].lower(), 0), reverse=True)
        elif sort_by == "findings":
            items.sort(key=lambda x: x["findings_count"], reverse=True)
        else:
            items.sort(key=lambda x: x["identifier"])

        paginated_items = items[offset : offset + limit]

        return paginated_items, counts
