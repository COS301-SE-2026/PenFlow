import json
import logging
import os
import re
import time
from pathlib import Path

import httpx

# Logger to track this specific worker
logger = logging.getLogger(__name__)
CRT_SH_PROVIDER = "crt.sh"
SCAN_MODE = os.getenv("SCAN_MODE", "MOCK").upper()
WORKERS_ROOT = Path(__file__).resolve().parent.parent.parent
_HOSTNAME_LABEL_PATTERN = re.compile(
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
)

def _normalize_hostname(value: str) -> str | None:
    hostname = value.strip().lower().rstrip(".")

    if not hostname or hostname.startswith("*."):
        return None

    try:
        hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError:
        return None

    if len(hostname) > 253:
        return None

    labels = hostname.split(".")
    if any(_HOSTNAME_LABEL_PATTERN.fullmatch(label) is None for label in labels):
        return None

    return hostname


def build_active_scan_scope(
        domain: str,
        discovered_names: list[str],
        max_hostnames: int = 10,
) -> list[str]:
    apex = _normalize_hostname(domain)

    if apex is None or max_hostnames < 1:
        return []

    suffix = f".{apex}"
    scoped_names = {apex}

    for name in discovered_names:
        if not isinstance(name, str):
            continue

        hostname = _normalize_hostname(name)
        if hostname is None:
            continue

        if hostname == apex or hostname.endswith(suffix):
            scoped_names.add(hostname)

    ordered_names = [
        apex,
        *sorted(scoped_names - {apex}),
    ]

    return ordered_names[:max_hostnames]


# collect raw data from mocks or from crt.sh depending on mode
def fetch_mock_data(domain: str) -> dict:
    """Collects subdomain and certificate data from crt.sh (Mock or Live)."""

    # Mock mode
    if SCAN_MODE == "MOCK":
        logger.info(f"[CRT.sh] Running in MOCK mode for {domain}")
        safe_domain = domain.replace(".", "_")
        mock_file = WORKERS_ROOT / "docs" / "raw_samples" / f"CrtSh_{safe_domain}.json"

        if not mock_file.exists():
            mock_file = WORKERS_ROOT / "docs" / "raw_samples" / "CrtSh_Response.json"

        try:
            with open(mock_file, "r") as f:
                data = json.load(f)
                # wrap the raw list in a dictionary so our pipeline stays consistent
                return {"certificates": data}
        except FileNotFoundError:
            logger.error("X Mock file not found. Returning empty dict.")
            return {"certificates": []}
    return {}


def fetch_live_data(domain: str) -> dict:
    # Live Mode
    logger.info(f"[CRT.sh] Running in FULL LIVE mode for {domain}")
    url = f"https://crt.sh/?q=%.{domain}&output=json&exclude=expired"
    # crt.sh is very bad with reliable requests,
    # we have to do a lot of retry logic to try get a good response.
    max_attempts = 4
    timeout_seconds = 6.0
    retry_delays = (0.5, 1.0, 2.0)
    retryable_status_codes = {429, 502, 503, 504}

    with httpx.Client(
        follow_redirects=True,
        headers={
            "Accept": "application/json",
            "User-Agent": "PenFlow/1.0",
        },
    ) as client:
        for attempt in range(1, max_attempts + 1):
            logger.info(
                f"[CRT.sh] Polling database (Attempt {attempt}/{max_attempts}) "
                f"with {timeout_seconds}s timeout..."
            )
            try:
                # crt.sh can be slow to respond, so we set a long timeout
                res = client.get(url, timeout=timeout_seconds)

                # Catch 502 Bad Gateway / 503 Service Unavailable natively
                if res.status_code in retryable_status_codes:
                    logger.warning(
                        f"[CRT.sh] Server returned "
                        f"{res.status_code}. Retrying..."
                    )
                else:
                    res.raise_for_status()

                    if not res.text.strip():
                        logger.warning(
                            "[CRT.sh] Returned a blank response. Retrying..."
                        )
                    else:
                        try:
                            certificates = res.json()
                        except json.JSONDecodeError:
                            logger.warning("[CRT.sh] Returned invalid JSON. Retrying...")
                        else:
                            if isinstance(certificates, list):
                                return {
                                    "certificates": certificates,
                                }

                            logger.warning("[CRT.sh] Returned an unexpected JSON payload. Retrying...")
            except httpx.TimeoutException:
                logger.warning(f"[CRT.sh] Timeout reached ({timeout_seconds}s). Retrying...")

            except httpx.HTTPError as e:
                logger.warning(f"[CRT.sh] HTTP Error: {e}. Retrying...")

            if attempt < max_attempts:
                time.sleep(retry_delays[attempt - 1])

        # If we exhaust all 5 attempts, fail gracefully
        logger.error(f"[CRT.sh] X Completely failed after {max_attempts} attempts.")
        return {"error": "API Request Failed / Timed Out"}


def collect_raw_data(domain: str) -> dict:
    """Collects subdomain and certificate data from crt.sh (Mock or Live)."""
    if SCAN_MODE == "MOCK":
        return fetch_mock_data(domain)

    return fetch_live_data(domain)


def normalize_data(raw_data: dict) -> dict:
    """
    Extracts and normalizes subdomains from raw crt.sh JSON.
    Removes all duplicates.
    """

    if "error" in raw_data:
        return {
            "subdomains": {
                "provider": CRT_SH_PROVIDER,
                "total_found": 0,
                "discovered_names": [],
                "error": raw_data.get("error"),
            }
        }

    logger.info("Normalizing crt.sh data:")

    unique_subdomains = set()
    certificates = raw_data.get("certificates", [])

    for cert in certificates:
        # Safe extraction of the domain string
        name_value = cert.get("name_value", "")
        split_names = name_value.split("\n")

        for name in split_names:
            name = name.strip().lower()
            if name and not name.startswith("*."):
                unique_subdomains.add(name)

    # Convert the set back to a sorted list so the JSON output is consistent and readable
    discovered_names = sorted(unique_subdomains)

    # format it into our strict schema
    normalized_subdomains = []
    for sub in discovered_names:
        normalized_subdomains.append({"subdomain": sub})

    return {
        "subdomains": {
            "provider": CRT_SH_PROVIDER,
            "total_found": len(discovered_names),
            "discovered_names": discovered_names,
        }
    }


# analyze subdomains for potential risks and extract assets
def generate_findings_and_assets(normalized_data: dict) -> tuple:
    findings = []
    assets = []

    subdomains = normalized_data.get("subdomains", {})

    if "error" in subdomains:
        return findings, assets

    for subdomain in subdomains.get("discovered_names", []):
        assets.append(
            {
                "asset_type": "subdomain",
                "identifier": subdomain,
                "asset_metadata": {
                    "source": CRT_SH_PROVIDER,
                },
            }
        )

    return findings, assets
