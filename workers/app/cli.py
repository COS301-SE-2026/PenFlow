import argparse
import json
import logging
import os
import sys
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Any

from app.services.fingerprinting_service import FingerprintingService
from app.services.http_security_service import (
    HTTP_PORTS,
    HTTPS_PORTS,
    run_http_security_scan,
)
from app.services.nmap_service import run_live_nmap_scan
from app.services.tls_service import TLS_PORTS, run_tls_scan
from app.utils.callback import send_source_callback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PipelineHandler = Callable[
    [dict[str, Any]],
    dict[str, Any],
]

_MIN_PIPELINE_CONCURRENCY = 1
_DEFAULT_PIPELINE_CONCURRENCY = 3
_MAX_PIPELINE_CONCURRENCY = 4

_PIPELINE_SOURCES = (
    "nmap",
    "http_security",
    "tls",
    "fingerprint",
)


def _get_pipeline_concurrency() -> int:
    try:
        configured = int(
            os.getenv(
                "PHASE2_SCAN_CONCURRENCY",
                str(_DEFAULT_PIPELINE_CONCURRENCY),
            )
        )
    except ValueError:
        configured = _DEFAULT_PIPELINE_CONCURRENCY

    return min(
        max(
            configured,
            _MIN_PIPELINE_CONCURRENCY,
        ),
        _MAX_PIPELINE_CONCURRENCY,
    )


def _is_http_service(
        port: dict[str, Any],
) -> bool:
    port_number = int(port["port"])
    service = str(
        port.get("service") or ""
    ).lower()

    return (
        port_number in HTTP_PORTS
        or port_number in HTTPS_PORTS
        or "http" in service
    )


def _is_tls_service(
        port: dict[str, Any],
) -> bool:
    service = str(
        port.get("service") or ""
    ).lower()

    return (
        int(port["port"]) in TLS_PORTS
        or "https" in service
        or "ssl" in service
        or "tls" in service
    )


def _build_pipeline_target(
        hostname: str,
        ports: list[dict[str, Any]],
) -> tuple[str, dict[str, Any]] | None:
    web_ports = [
        port
        for port in ports
        if _is_http_service(port)
    ]

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
    service = str(
        selected.get("service") or ""
    ).lower()

    scheme = (
        "https"
        if (
            port_number in HTTPS_PORTS
            or "https" in service
            or "ssl" in service
            or "tls" in service
        )
        else "http"
    )

    port_suffix = (
        ""
        if port_number in (80, 443)
        else f":{port_number}"
    )

    return (
        f"{scheme}://{hostname}{port_suffix}",
        selected,
    )


def _pipeline_source_status(
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


def _send_pipeline_progress(
        scan_id: str,
        source_name: str,
        total_targets: int,
        completed_targets: int,
        failed_targets: int,
        finished: bool,
) -> None:
    status = (
        _pipeline_source_status(
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

    send_source_callback(
        scan_id=scan_id,
        source_name=source_name,
        status=status,
        raw_result={
            "attempted_targets": total_targets,
            "completed_targets": completed_targets,
            "failed_targets": failed_targets,
        },
        error_message=error_message,
        total_targets=total_targets,
        completed_targets=completed_targets,
        failed_targets=failed_targets,
    )


def safe_failure_callback(
        scan_id: str, 
        source_name: str, 
        error: Exception,
        defer_source_completion: bool = False,
) -> None:
    try:
        send_source_callback(
            scan_id=scan_id,
            source_name=source_name,
            status="running" if defer_source_completion else "failed",
            raw_result={"error": str(error)},
            error_message=str(error),
        )
    except Exception as cb_e:
        logger.error(f"Failed to send failures callback for {source_name}: {cb_e}")


def handle_nmap(payload: dict[str, Any]) -> dict[str, Any]:
    scan_id = payload["scan_id"]
    defer_source_completion = bool(
        payload.get("defer_source_completion", False)
    )
    try:
        send_source_callback(scan_id=scan_id, source_name="nmap", status="running")
        scan_data = run_live_nmap_scan(
            ip_address=payload["ip_address"], profile=payload.get("profile", "standard")
        )

        services = [
            {
                "host": scan_data["ip"],
                "port": p["port"],
                "protocol": p["protocol"],
                "service_name": p["service"],
                "product": p["product"],
                "version": p["version"],
                "banner": p.get("extra_info"),
                "state": p["state"],
                "tls_enabled": False,
            }
            for p in scan_data.get("ports", [])
        ]
        send_source_callback(
            scan_id=scan_id,
            source_name="nmap",
            status="running" if defer_source_completion else "completed",
            raw_result=scan_data,
            services=services,
        )

        return scan_data

    except Exception as error:
        logger.exception(f"NMAP failed: {error}")
        safe_failure_callback(scan_id, "nmap", error, defer_source_completion)
        raise


def handle_tls(payload: dict[str, Any]) -> dict[str, Any]:
    scan_id = payload["scan_id"]
    defer_source_completion = bool(
        payload.get("defer_source_completion", False)
    )
    ip_address = payload["ip_address"]
    try:
        send_source_callback(scan_id=scan_id, source_name="tls", status="running")
        tls_data = run_tls_scan(
            ip_address=ip_address, ports=payload["ports"], hostname=payload.get("hostname")
        )

        findings = []
        for target in tls_data.get("targets", []):
            if "error" in target:
                findings.append(
                    {
                        "source": "tls",
                        "title": "TLS Handshake Failed",
                        "description": target["error"],
                        "recommendation": "Review TLS configuration.",
                        "severity": "low",
                        "host": ip_address,
                        "port": target["port"],
                        "protocol": "tcp",
                        "evidence": {"error": target["error"]},
                    }
                )
                continue

            cert = target.get("certificate", {})
            if cert.get("expired"):
                findings.append(
                    {
                        "source": "tls",
                        "title": "Expired TLS Certificate",
                        "description": "The TLS certificate has expired.",
                        "recommendation": "Renew the certificate.",
                        "severity": "high",
                        "host": ip_address,
                        "port": target["port"],
                        "protocol": "tcp",
                        "evidence": cert,
                    }
                )
            if cert.get("self_signed"):
                findings.append(
                    {
                        "source": "tls",
                        "title": "Self-Signed TLS Certificate",
                        "description": "Using a self-signed certificate.",
                        "recommendation": "Use a trusted CA.",
                        "severity": "medium",
                        "host": ip_address,
                        "port": target["port"],
                        "protocol": "tcp",
                        "evidence": {"subject": cert.get("subject"), "issuer": cert.get("issuer")},
                    }
                )

        send_source_callback(
            scan_id=scan_id,
            source_name="tls",
            status="running" if defer_source_completion else "completed",
            raw_result=tls_data,
            findings=findings,
        )

        return tls_data

    except Exception as error:
        logger.exception(f"TLS failed: {error}")
        safe_failure_callback(scan_id, "tls", error, defer_source_completion)
        raise


def handle_http_security(payload: dict[str, Any]) -> dict[str, Any]:
    scan_id = payload["scan_id"]
    defer_source_completion = bool(
        payload.get("defer_source_completion", False)
    )
    ip_address = payload["ip_address"]
    hostname = payload["hostname"]
    try:
        send_source_callback(scan_id=scan_id, source_name="http_security", status="running")
        scan_data = run_http_security_scan(
            hostname=hostname, ip_address=ip_address, ports=payload["ports"]
        )

        findings = []
        for target in scan_data.get("targets", []):
            headers = target.get("security_headers", {})
            if not headers.get("content_security_policy") and not headers.get(
                "content_security_policy_report_only"
            ):
                findings.append(
                    {
                        "source": "http_security",
                        "severity": "low",
                        "title": "Missing Content-Security-Policy",
                        "description": "No CSP present.",
                        "recommendation": "Create a CSP header.",
                        "host": hostname,
                        "port": target["port"],
                        "protocol": "tcp",
                        "evidence": {"url": target["url"], "header": "Content-Security-Policy"},
                    }
                )

            checks = {
                "X-Frame-Options": headers.get("x_frame_options"),
                "Referrer-Policy": headers.get("referrer_policy"),
                "Permissions-Policy": headers.get("permissions_policy"),
                "X-Content-Type-Options": headers.get("x_content_type_options"),
            }
            if target.get("scheme") == "https":
                checks["Strict-Transport-Security"] = headers.get("strict_transport_security")

            for h_name, h_val in checks.items():
                if not h_val:
                    findings.append(
                        {
                            "source": "https_security",
                            "severity": "low",
                            "title": f"Missing {h_name}",
                            "description": f"{h_name} missing.",
                            "recommendation": f"Configure {h_name}.",
                            "host": hostname,
                            "port": target["port"],
                            "protocol": "tcp",
                            "evidence": {"url": target["url"], "header": h_name},
                        }
                    )

        send_source_callback(
            scan_id=scan_id,
            source_name="http_security",
            status="running" if defer_source_completion else "completed",
            raw_result=scan_data,
            findings=findings,
        )

        return scan_data

    except Exception as error:
        logger.exception(f"HTTP Security failed: {error}")
        safe_failure_callback(scan_id, "http_security", error, defer_source_completion)
        raise


def handle_fingerprint(payload: dict[str, Any]) -> dict[str, Any]:
    scan_id = payload["scan_id"]
    defer_source_completion = bool(
        payload.get("defer_source_completion", False)
    )
    target_url = payload["target_url"]
    try:
        send_source_callback(scan_id=scan_id, source_name="fingerprint", status="running")

        svc = FingerprintingService(
            target_url=target_url,
            nmap_data=payload.get("nmap_data", {}),
            tls_data=payload.get("tls_data", {}),
        )
        fingerprint_results = svc.run()

        software_list = fingerprint_results.get("fingerprint", {}).get("software", [])
        nmap_ports = payload.get("nmap_data", {}).get("ports", [])
        technologies = []
        confidence_map = {"low": 0.40, "medium": 0.70, "high": 0.95}

        for sw in software_list:
            conf_label = sw.get("confidence", "low")
            software_product = str(
                sw.get("product") or ""
            ).strip().lower()

            matching_ports = [
                port
                for port in nmap_ports
                if (
                    software_product
                    and str(
                        port.get("product") or ""
                    ).strip().lower()
                    and (
                        software_product
                        in str(
                            port.get("product") or ""
                        ).strip().lower()
                        or str(
                            port.get("product") or ""
                        ).strip().lower()
                        in software_product
                    )
                )
            ]

            technology_services = (
                matching_ports
                or [
                    {
                        "port": payload["service_port"],
                        "protocol": payload["service_protocol"],
                    }
                ]
            )

            for service in technology_services:
                technologies.append(
                    {
                        "technology_type": sw.get("category", "unknown"),
                        "product": sw.get("product", "unknown"),
                        "version": sw.get("version"),
                        "confidence": confidence_map.get(conf_label, 0.40),
                        "detection_source": "fingerprint",
                        "host": payload["ip_address"],
                        "port": int(service["port"]),
                        "protocol": str(
                            service.get("protocol")
                            or "tcp"
                        ),
                        "evidence": {
                            "vendor": sw.get("vendor"),
                            "evidence_source": sw.get("evidence_score", 0),
                            "sources": sw.get("sources", []),
                            "confidence_label": conf_label,
                            "target_url": target_url,
                        },
                    }
                )

        send_source_callback(
            scan_id=scan_id,
            source_name="fingerprint",
            status="running" if defer_source_completion else "completed",
            raw_result=fingerprint_results,
            technologies=technologies,
        )

        return fingerprint_results

    except Exception as error:
        logger.exception(f"Fingerprinting failed: {error}")
        safe_failure_callback(scan_id, "fingerprint", error, defer_source_completion)
        raise


def handle_phase2_pipeline(
        payload: dict[str, Any],
) -> dict[str, Any]:
    scan_id = payload["scan_id"]
    targets = payload.get("targets", [])
    profile = payload.get("profile", "standard")

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
            address_to_hostnames.setdefault(
                address,
                [],
            )

            if hostname not in address_to_hostnames[address]:
                address_to_hostnames[address].append(
                    hostname
                )

    logger.info(
        "[PHASE2_PIPELINE] Starting Isolated scan "
        "for %s unique address(es)",
        len(address_to_hostnames),
    )

    failed_counts = {
        source_name: 0
        for source_name in _PIPELINE_SOURCES
    }

    completed_counts = {
        source_name: 0
        for source_name in _PIPELINE_SOURCES
    }

    nmap_total = len(address_to_hostnames)

    _send_pipeline_progress(
        scan_id,
        "nmap",
        nmap_total,
        0,
        0,
        finished=nmap_total == 0,
    )

    nmap_results: dict[
        str,
        dict[str, Any],
    ] = {}

    nmap_worker_count = min(
        _get_pipeline_concurrency(),
        max(nmap_total, 1),
    )

    with ThreadPoolExecutor(
        max_workers=nmap_worker_count,
    ) as executor:
        future_to_address: dict[
            Future[dict[str, Any]],
            str,
        ] = {
            executor.submit(
                handle_nmap,
                {
                    "scan_id": scan_id,
                    "ip_address": ip_address,
                    "profile": profile,
                    "defer_source_completion": True,
                },
            ): ip_address
            for ip_address in address_to_hostnames
        }

        for future in as_completed(
            future_to_address
        ):
            ip_address = future_to_address[future]

            try:
                nmap_results[ip_address] = (
                    future.result()
                )
                completed_counts["nmap"] += 1
            except Exception:
                logger.exception(
                    "[PHASE2_PIPELINE] Nmap failed "
                    "for %s",
                    ip_address,
                )
                failed_counts["nmap"] += 1

            processed_targets = (
                completed_counts["nmap"]
                + failed_counts["nmap"]
            )

            _send_pipeline_progress(
                scan_id,
                "nmap",
                nmap_total,
                completed_counts["nmap"],
                failed_counts["nmap"],
                finished=(
                    processed_targets == nmap_total
                ),
            )

    http_jobs: list[dict[str, Any]] = []
    tls_jobs: list[dict[str, Any]] = []
    fingerprint_jobs: list[dict[str, Any]] = []

    http_scanned_hostnames: set[str] = set()
    fingerprinted_hostnames: set[str] = set()

    for ip_address in sorted(nmap_results):
        scan_data = nmap_results[ip_address]
        ports = scan_data.get("ports", [])
        hostnames = address_to_hostnames.get(
            ip_address,
            [],
        )

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
            if (
                http_ports
                and hostname
                not in http_scanned_hostnames
            ):
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

            fingerprint_target = (
                _build_pipeline_target(
                    hostname,
                    ports,
                )
            )

            if (
                fingerprint_target is not None
                and hostname
                not in fingerprinted_hostnames
            ):
                fingerprinted_hostnames.add(
                    hostname
                )

                (
                    target_url,
                    target_service,
                ) = fingerprint_target

                fingerprint_jobs.append(
                    {
                        "scan_id": scan_id,
                        "hostname": hostname,
                        "ip_address": ip_address,
                        "target_url": target_url,
                        "service_port": int(
                            target_service["port"]
                        ),
                        "service_protocol": str(
                            target_service.get(
                                "protocol"
                            )
                            or "tcp"
                        ),
                        "nmap_data": {
                            "ports": ports,
                        },
                        "tls_data": {},
                        "defer_source_completion": True,  
                    }
                )

    job_plans: dict[
        str,
        tuple[
            list[dict[str, Any]],
            PipelineHandler,
        ],
    ] = {
        "http_security": (
            http_jobs,
            handle_http_security,
        ),
        "tls": (
            tls_jobs,
            handle_tls,
        ),
        "fingerprint": (
            fingerprint_jobs,
            handle_fingerprint,
        ),
    }

    downstream_jobs: list[
        tuple[
            str,
            dict[str, Any],
            PipelineHandler,
        ]
    ] = []

    for source_name, (
        jobs,
        handler,
    ) in job_plans.items():
        _send_pipeline_progress(
            scan_id,
            source_name,
            len(jobs),
            0,
            0,
            finished=len(jobs) == 0,
        )

        downstream_jobs.extend(
            (
                source_name,
                job,
                handler,
            )
            for job in jobs
        )

    downstream_worker_count = min(
        _get_pipeline_concurrency(),
        max(len(downstream_jobs), 1),
    )

    with ThreadPoolExecutor(
        max_workers=downstream_worker_count,
    ) as executor:
        future_to_job: dict[
            Future[dict[str, Any]],
            tuple[
                str,
                dict[str, Any],
            ],
        ] = {
            executor.submit(
                handler,
                job,
            ): (
                source_name,
                job,
            )
            for (
                source_name,
                job,
                handler,
            ) in downstream_jobs
        }

        for future in as_completed(
            future_to_job
        ):
            source_name, job = future_to_job[future]

            try:
                future.result()
                completed_counts[source_name] += 1
            except Exception:
                logger.exception(
                    "[PHASE2_PIPELINE] %s failed "
                    "for %s",
                    source_name,
                    job.get("hostname")
                    or job.get("ip_address"),
                )
                failed_counts[source_name] += 1

            total_targets = len(
                job_plans[source_name][0]
            )
            processed_targets = (
                completed_counts[source_name]
                + failed_counts[source_name]
            )

            _send_pipeline_progress(
                scan_id,
                source_name,
                total_targets,
                completed_counts[source_name],
                failed_counts[source_name],
                finished=(
                    processed_targets == total_targets
                ),
            )

    overall_status = (
        "partial"
        if any(failed_counts.values())
        else "completed"
    )

    logger.info(
        "[PHASE2_PIPELINE] Finished scan %s "
        "with status %s",
        scan_id,
        overall_status,
    )

    return {
        "status": overall_status,
        "scan_id": scan_id,
        "source_name": "phase2_pipeline",
        "unique_addresses": len(address_to_hostnames),
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("tool", type=str)
    parser.add_argument("--payload", type=str, required=True)
    args = parser.parse_args()

    try:
        payload = json.loads(args.payload)
        scan_id = payload.get("scan_id", "unknown")

        if args.tool == "phase2_pipeline":
            handle_phase2_pipeline(payload)
        elif args.tool == "nmap":
            handle_nmap(payload)
        elif args.tool == "tls":
            handle_tls(payload)
        elif args.tool == "http_security":
            handle_http_security(payload)
        elif args.tool == "fingerprint":
            handle_fingerprint(payload)
        else:
            raise ValueError(f"Unknown tool requested: {args.tool}")

        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error in CLI for {args.tool}: {e}")
        try:
            payload = json.loads(args.payload)
            scan_id = payload.get("scan_id")
            if scan_id:
                if args.tool == "phase2_pipeline":
                    for source_name in _PIPELINE_SOURCES:
                        safe_failure_callback(
                            scan_id,
                            source_name,
                            e,
                        )
                else:
                    safe_failure_callback(
                        scan_id,
                        args.tool,
                        e,
                        bool(
                            payload.get(
                                "defer_source_completion",
                                False,
                            )
                        ),
                    )
        except Exception:
            pass
        sys.exit(1)
