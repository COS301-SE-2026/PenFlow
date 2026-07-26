import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]


class CVEService:
    def __init__\
    (
        self,
        resolved_inventory: list[JSONDict],
    ):
        self.resolved_inventory = resolved_inventory
        self.vulnerabilities = []

    def run(self) -> list[JSONDict]:
        logger.info\
        (
            f"[CVE_Service] Processing {len(self.resolved_inventory)} resolved components."
        )

        #go through all software found by fingerprinting
        #and only if versions and cpe are present:
        #do we query NVD
        for software in self.resolved_inventory:
            if software.get("confidence") == "low":
                continue

            target_cpe = software.get("cpe")

            if not target_cpe:
                continue

            cpe_parts = target_cpe.split(":")

            #skip wildcards
            #wildcards return all instances of that software from NVD(thousands)
            if len(cpe_parts) > 5 and cpe_parts[5] == "*":
                logger.warning\
                (
                    f"[CVE_Service] Skipping {software.get('product')}: "
                    "No exact version discovered."
                )
                continue

            cves = self._lookup_nvd\
            (
                target_cpe,
                software,
            )

            self.vulnerabilities.extend(cves)

        return self._deduplicate()

    def _deduplicate(self) -> list[JSONDict]:
        seen = set()
        unique_vulnerabilities = []

        #only need one cve if multiple come through
        for vulnerability in self.vulnerabilities:
            identifier = \
            (
                vulnerability.get("cve_id"),
                vulnerability.get("host"),
                vulnerability.get("port"),
                vulnerability.get("protocol"),
                vulnerability.get("affected_software"),
            )

            if identifier in seen:
                continue

            seen.add(identifier)
            unique_vulnerabilities.append(vulnerability)

        return unique_vulnerabilities

    def _lookup_nvd\
    (
        self,
        cpe: str,
        software: JSONDict,
    ) -> list[JSONDict]:

        discovered_cves = []

        #query the official nvd api using the cpe's provided by the previous worker
        url = "https://services.nvd.nist.gov/rest/json/cves/2.0"

        params = \
        {
            "virtualMatchString": cpe,
        }

        try:
            logger.warning\
            (
                f"[CVE_Service] Querying NVD for: {cpe}"
            )

            response = requests.get\
            (
                url,
                params=params,
                timeout=15,
            )

            if response.status_code == 200:
                data = response.json()

                #validate each vulnerability
                for item in data.get("vulnerabilities", []):
                    cve = item["cve"]

                    is_valid = False

                    #nvd keeps old data that seems to imply all versions have vulnerabilities
                    #we need to look specifically at versions we want
                    for configuration in cve.get("configurations", []):
                        for node in configuration.get("nodes", []):
                            for match in node.get("cpeMatch", []):

                                if not match.get("vulnerable"):
                                    continue

                                if \
                                (
                                    "versionEndIncluding" in match
                                    or
                                    "versionEndExcluding" in match
                                ):
                                    is_valid = True
                                    break

                                criteria = match.get("criteria", "")
                                criteria_parts = criteria.split(":")

                                if \
                                (
                                    len(criteria_parts) > 5
                                    and
                                    criteria_parts[5] not in ("*", "-")
                                ):
                                    is_valid = True
                                    break

                            if is_valid:
                                break

                        if is_valid:
                            break

                    if not is_valid:
                        continue

                    metrics_v3 = \
                    (
                        cve.get("metrics", {})
                        .get("cvssMetricV31", [{}])[0]
                    )

                    metrics_v2 = \
                    (
                        cve.get("metrics", {})
                        .get("cvssMetricV2", [{}])[0]
                    )

                    severity = \
                    (
                        metrics_v3.get("cvssData", {}).get("baseSeverity")
                        or
                        metrics_v2.get("baseSeverity", "UNKNOWN")
                    )

                    score = \
                    (
                        metrics_v3.get("cvssData", {}).get("baseScore")
                        or
                        metrics_v2.get("cvssData", {}).get("baseScore", 0)
                    )

                    discovered_cves.append\
                    (
                        {
                            "cve_id": cve["id"],
                            "severity": str(severity).upper(),
                            "cvss_score": score,
                            "description": cve["descriptions"][0]["value"],
                            "affected_software": software.get(
                                "product",
                                "unknown",
                            ),
                            "affected_version": software.get("version"),
                            "cpe": cpe,
                            "host": software.get("host"),
                            "port": software.get("port"),
                            "protocol": software.get("protocol"),
                            "remediation": "Check NVD reference links for patches.",
                        }
                    )

            else:
                logger.warning\
                (
                    f"[CVE_Service] NVD returned HTTP {response.status_code} for {cpe}"
                )

        except Exception as error:
            logger.error\
            (
                f"[CVE_Service] NVD API error for {cpe}: {error}"
            )

        return discovered_cves


def run_cve_scan\
(
    resolved_inventory: list[JSONDict],
) -> list[JSONDict]:
    service = CVEService\
    (
        resolved_inventory,
    )

    return service.run()