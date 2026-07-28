import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]


class CVEService:
    def __init__(
        self,
        resolved_inventory: list[JSONDict],
    ):
        self.resolved_inventory = resolved_inventory
        self.vulnerabilities = []

    def run(self) -> list[JSONDict]:
        logger.info(f"[CVE_Service] Processing {len(self.resolved_inventory)} resolved components.")

        # go through all software found by fingerprinting
        # and only if versions and cpe are present:
        # do we query NVD
        for software in self.resolved_inventory:
            if software.get("confidence") == "low":
                continue

            target_cpe = software.get("cpe")

            if not target_cpe:
                continue

            cves = self._lookup_nvd(
                target_cpe,
                software,
            )

            self.vulnerabilities.extend(cves)

        return self._deduplicate()

    def _deduplicate(self) -> list[JSONDict]:
        seen = set()
        unique_vulnerabilities = []

        # only need one cve if multiple come through
        for vulnerability in self.vulnerabilities:
            identifier = f"{vulnerability['cve_id']}_{vulnerability['affected_software']}"

            if identifier in seen:
                continue

            seen.add(identifier)
            unique_vulnerabilities.append(vulnerability)

        return unique_vulnerabilities

    def _lookup_nvd(
        self,
        cpe: str,
        software: JSONDict,
    ) -> list[JSONDict]:

        discovered_cves = []
        cpe_parts = cpe.split(":")
        version = cpe_parts[5] if len(cpe_parts) > 5 else "*"
        vendor = software.get("vendor", "").lower()
        product = software.get("product", "").lower()

        # query the official nvd api using the cpe's provided by the previous worker
        url = "https://services.nvd.nist.gov/rest/json/cves/2.0"

    #nvd api doc alignment
        params = \
        {
            "cpeName": cpe,
            "resultsPerPage":50,
        }

        try:
            logger.warning(f"[CVE_Service] Querying NVD for: {cpe}")

            response = requests.get\
            (
                url,
                params=params,
                timeout=15,
            )

            if response.status_code != 200:
                logger.warning\
                (
                    f"[CVE_Service] NVD returned HTTP {response.status_code} for {cpe}"
                )
                return []

            data = response.json()
            vulnerability_list = data.get("vulnerabilities", [])

            #temporarily we allow 1 wildcard through to get some cve info
            #force newest first
            vulnerability_list.sort\
            (
                key=lambda item: item["cve"].get("published", ""),
                reverse=True,
            )
            if version == "*":
                vulnerability_list = vulnerability_list[:1]
            else:
                vulnerability_list = vulnerability_list[:20]

            #best method to ignore plugins and additions and so on
            ignored_terms = \
            [
                "mod_",
                "apache::",
                "apache2::",
                "status.pm",
                "mod_perl",
                "perl-status",
                "apache::status",
            ]

            # validate each vulnerability
            for item in vulnerability_list:
                cve = item["cve"]

                description = ""

                for desc in cve.get("descriptions", []):
                    if desc.get("lang") == "en":
                        description = desc.get("value", "")
                        break

                desc_lower =description.lower()
                # Ignore module-specific CVEs
                if any(term in desc_lower for term in ignored_terms):
                    continue

                # If our product isn't even mentioned, skip it.
                if product:
                    if \
                    (
                            product.replace("_", " ") not in desc_lower
                            and product.replace("-", " ") not in desc_lower
                    ):
                        continue

                metrics = \
                (
                        cve.get("metrics", {}).get("cvssMetricV31")
                        or cve.get("metrics", {}).get("cvssMetricV30")
                        or cve.get("metrics", {}).get("cvssMetricV2")
                        or []
                )

                severity = "UNKNOWN"
                score = 0

                if metrics:
                    metric = metrics[0]

                    if "cvssData" in metric:
                        severity = metric["cvssData"].get\
                        (
                            "baseSeverity",
                            metric.get("baseSeverity", "UNKNOWN"),
                        )

                        score = metric["cvssData"].get\
                        (
                            "baseScore",
                            metric.get("baseScore", 0),
                        )

                    else:
                        severity = metric.get("baseSeverity", "UNKNOWN")
                        score = metric.get("baseScore", 0)


                discovered_cves.append\
                (
                    {
                        "cve_id": cve["id"],
                        "severity": str(severity).upper(),
                        "cvss_score": score,
                        "description": description,
                        "affected_software": cpe,
                        "remediation": "Check NVD reference links for patches.",
                    }
                )

            else:
                logger.warning(f"[CVE_Service] NVD returned HTTP {response.status_code} for {cpe}")

        except Exception as error:
            logger.error(f"[CVE_Service] NVD API error for {cpe}: {error}")

        return discovered_cves


def run_cve_scan(
    resolved_inventory: list[JSONDict],
) -> list[JSONDict]:
    service = CVEService(
        resolved_inventory,
    )

    return service.run()
