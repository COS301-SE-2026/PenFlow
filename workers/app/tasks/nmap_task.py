import logging
import os
from collections.abc import Iterator
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Any

from app.queue.celery_app import celery_app
from app.services.http_security_service import HTTP_PORTS, HTTPS_PORTS
from app.services.tls_service import TLS_PORTS
from app.utils.callback import send_source_callback
from app.utils.db_utils import get_ports_from_db, get_technologies_from_db
from app.utils.job_runner import dispatch_scan_job

logger = logging.getLogger(__name__)

_ACTIVE_SOURCES = (
    "nmap",
    "http_security",
    "tls",
    "fingerprint",
)

_MIN_SCAN_CONCURRENCY = 1
_DEFAULT_SCAN_CONCURRENCY = 3
_MAX_SCAN_CONCURRENCY = 4


def _get_scan_concurrency() -> int:
    try:
        configured = int(
            os.getenv(
                "PHASE2_SCAN_CONCURRENCY",
                str(_DEFAULT_SCAN_CONCURRENCY),
            )
        )
    except ValueError:
        configured = _DEFAULT_SCAN_CONCURRENCY

    return min(
        max(configured, _MIN_SCAN_CONCURRENCY),
        _MAX_SCAN_CONCURRENCY,
    )


def _dispatch_jobs(
        source_name: str,
        jobs: list[dict[str, Any]],
) -> Iterator[tuple[dict[str, Any], bool]]:
    if not jobs:
        return

    worker_count = min(
        _get_scan_concurrency(),
        len(jobs),
    )

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_to_payload: dict[
            Future[bool],
            dict[str, Any],
        ] = {
            executor.submit(
                dispatch_scan_job,
                source_name,
                payload,
            ): payload
            for payload in jobs
        }

        for future in as_completed(future_to_payload):
            payload = future_to_payload[future]

            try:
                succeeded = future.result()
            except Exception:
                logger.exception(
                    "[NMAP_TASK] %s target job raised unexpectedly",
                    source_name,
                )
                succeeded = False

            yield payload, succeeded


def _is_http_service(port: dict[str, Any]) -> bool:
    port_number = int(port["port"])
    service = str(port.get("service") or "").lower()
    return (
        port_number in HTTP_PORTS
        or port_number in HTTPS_PORTS
        or "http" in service
    )


def _is_tls_service(port: dict[str, Any]) -> bool:
    service = str(port.get("service") or "").lower()
    return (
        int(port["port"]) in TLS_PORTS
        or "https" in service
        or "ssl" in service
        or "tls" in service
    )


def _build_target_url(
        hostname: str,
        ports: list[dict[str, Any]],
) -> str | None:
    web_ports = [port for port in ports if _is_http_service(port)]
    if not web_ports:
        return None

    web_ports.sort(
        key=lambda port: (
            0
            if int(port["port"]) == 443
            else 1
            if int(port["port"]) == 80
            else 2,
            int(port["port"]),
        )
    )

    selected = web_ports[0]
    port_number = int(selected["port"])
    service = str(selected.get("service") or "").lower()
    scheme = (
        "https"
        if port_number in HTTPS_PORTS
        or "https" in service
        or "ssl" in service
        or "tls" in service
        else "http"
    )

    port_suffix = (
        ""
        if port_number in (80, 443)
        else f":{port_number}"
    )

    return f"{scheme}://{hostname}{port_suffix}"


def _final_source_status(
        attempted: int,
        failed: int,
) -> str:
    if attempted == 0:
        return "skipped"

    if failed == 0:
        return "completed"

    if failed == attempted:
        return "failed"

    return "partial"


def _send_target_progress(
        scan_id: str,
        source_name: str,
        total_targets: int,
        completed_targets: int,
        failed_targets: int,
        finished: bool,
) -> None:
    status = (
        _final_source_status(
            total_targets,
            failed_targets,
        )
        if finished
        else "running"
    )

    error_message = (
        f"{failed_targets} of "
        f"{total_targets} target jobs failed."
        if finished and failed_targets
        else None
    )

    raw_result = (
        {
            "attempted_targets": total_targets,
            "completed_targets": completed_targets,
            "failed_targets": failed_targets,
        }
        if finished
        else None
    )

    send_source_callback(
        scan_id=scan_id,
        source_name=source_name,
        status=status,
        raw_result=raw_result,
        error_message=error_message,
        total_targets=total_targets,
        completed_targets=completed_targets,
        failed_targets=failed_targets,
    )


@celery_app.task(
    name="scan.phase2_nmap",
    bind=True,
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def run_nmap_scan(
    self: Any,
    scan_id: str,
    targets: list[dict[str, Any]],
    profile: str = "standard",
) -> dict[str, Any]:
    """
    Coordinates bounded active scanning across resolved addresses and hostnames
    """

    address_to_hostnames: dict[str, list[str]] = {}

    for target in targets:
        hostname = target.get("hostname")
        if not hostname:
            continue

        addresses = [
            *target.get("ipv4", []),
            *target.get("ipv6", []),
        ]

        for address in addresses:
            address_to_hostnames.setdefault(address, [])

            if hostname not in address_to_hostnames[address]:
                address_to_hostnames[address].append(hostname)

    logger.info(
        "[NMAP_TASK] Coordinating active scans for %s unique address(es)",
        len(address_to_hostnames),
    )

    ports_by_addresses: dict[str, list[dict[str, Any]]] = {}
    failed_counts = {
        source: 0
        for source in _ACTIVE_SOURCES
    }

    nmap_total = len(address_to_hostnames)
    nmap_completed = 0

    _send_target_progress(
        scan_id,
        "nmap",
        nmap_total,
        nmap_completed,
        failed_counts["nmap"],
        finished=nmap_total == 0,
    )

    nmap_jobs = [
        {
            "scan_id": scan_id,
            "ip_address": ip_address,
            "profile": profile,
            "defer_source_completion": True,
        }
        for ip_address in address_to_hostnames
    ]

    for payload, nmap_success in _dispatch_jobs(
        "nmap",
        nmap_jobs,
    ):
        ip_address = str(payload["ip_address"])

        if nmap_success:
            nmap_completed += 1
            ports_by_addresses[ip_address] = get_ports_from_db(
                scan_id,
                ip_address,
            )
        else:
            failed_counts["nmap"] += 1

        processed_targets = (
            nmap_completed + failed_counts["nmap"]
        )

        _send_target_progress(
            scan_id,
            "nmap",
            nmap_total,
            nmap_completed,
            failed_counts["nmap"],
            finished=processed_targets == nmap_total,
        )

    http_jobs: list[dict[str, Any]] = []
    tls_jobs: list[dict[str, Any]] = []
    fingerprint_jobs: list[dict[str, Any]] = []

    http_scanned_hostnames: set[str] = set()
    fingerprinted_hostnames: set[str] = set()

    for ip_address in sorted(address_to_hostnames):
        hostnames = address_to_hostnames[ip_address]
        ports = ports_by_addresses.get(ip_address)
        if ports is None:
            continue

        http_ports = [
            port
            for port in ports
            if _is_http_service(port)
        ]

        tls_ports = [
            port
            for port in ports
            if _is_tls_service(port)
        ]

        for hostname in hostnames:
            if(http_ports and hostname not in http_scanned_hostnames):
                http_scanned_hostnames.add(hostname)
                http_jobs.append(
                    {
                        "scan_id": scan_id,
                        "hostname": hostname,
                        "ip_address": ip_address,
                        "ports": http_ports,
                        "defer_source_completion": True,
                    }
                )

            if tls_ports:
                tls_jobs.append(
                    {
                        "scan_id": scan_id,
                        "hostname": hostname,
                        "ip_address": ip_address,
                        "ports": tls_ports,
                        "defer_source_completion": True,
                    }
                )

            target_url = _build_target_url(hostname, ports)

            if(target_url is not None and hostname not in fingerprinted_hostnames):
                fingerprinted_hostnames.add(hostname)
                fingerprint_jobs.append(
                    {
                        "scan_id": scan_id,
                        "hostname": hostname,
                        "ip_address": ip_address,
                        "target_url": target_url,
                        "nmap_data": {
                            "ports": ports,
                        },
                        "tls_data": {},
                        "defer_source_completion": True,
                    }
                )

    job_plans = {
        "http_security": http_jobs,
        "tls": tls_jobs,
        "fingerprint": fingerprint_jobs,
    }

    for source_name, jobs in job_plans.items():
        total_targets = len(jobs)
        completed_targets = 0

        _send_target_progress(
            scan_id,
            source_name,
            total_targets,
            completed_targets,
            failed_counts[source_name],
            finished=total_targets == 0,
        )

        for payload in jobs:
            job_success = dispatch_scan_job(
                source_name,
                payload,
            )
            if job_success:
                completed_targets += 1
            else:
                failed_counts[source_name] += 1

            processed_targets = (
                completed_targets + failed_counts[source_name]
            )

            _send_target_progress(
                scan_id,
                source_name,
                total_targets,
                completed_targets,
                failed_counts[source_name],
                finished=processed_targets == total_targets,
            )

    inventory = get_technologies_from_db(scan_id)
    celery_app.send_task(
        "scan.phase2_cpe_resolver",
        args=[scan_id, inventory],
    )

    overall_status = (
        "partial"
        if any(failed_counts.values())
        else "completed"
    )

    return {
        "status": overall_status,
        "scan_id": scan_id,
        "source_name": "nmap",
        "unique_addresses": len(address_to_hostnames),
    }
