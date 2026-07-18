import logging
import re
from pathlib import Path
from typing import Any, Optional

import requests
import urllib3
from bs4 import BeautifulSoup

from app.services.signatures.cdn import CDN_SIGNATURES
from app.services.signatures.cms import CMS_SIGNATURES
from app.services.signatures.databases import DATABASE_SIGNATURES
from app.services.signatures.frameworks import FRAMEWORK_SIGNATURES
from app.services.signatures.languages import LANGUAGE_SIGNATURES
from app.services.signatures.load_balancers import LOAD_BALANCER_SIGNATURES
from app.services.signatures.servers import SERVER_SIGNATURES

#best way to silence the warnings for unsafe connections
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]


class FingerprintingService:
    def __init__ \
        (
            self,
            target_url: str,
            nmap_data: Optional[dict[str, Any]] = None,
            tls_data: Optional[dict[str, Any]] = None,
        ):
        self.target_url = target_url
        self.nmap_data = nmap_data or {}
        self.tls_data = tls_data or {}

        self.cache = \
        {
            "status_code": 0,
            "final_url": "",
            "headers": {},
            "cookies": {},
            "html_text": "",
            "title": "",
            "meta_tags": [],
            "scripts": [],
            "links": [],
        }

        self.discovered = {}

        self.telemetry = \
        {
                "unknown_server_strings": [],
                "unknown_powered_by": [],
                "unknown_generator": [],
                "unknown_headers": [],
                "unknown_cookies": [],
                "unknown_scripts": [],
                "unknown_meta": [],
        }

    def run(self) -> JSONDict:
        """
        Executes the fingerprinting pipeline and returns standardized software assets.
        """

        # collect http data
        self.collect_http_data()

        #signature evals check against records we keep to help identify systems like...
        # check web servers
        self._evaluate_signatures(SERVER_SIGNATURES)
        # check languages
        self._evaluate_signatures(LANGUAGE_SIGNATURES)
        # check content management systems
        self._evaluate_signatures(CMS_SIGNATURES)
        # check frameworks
        self._evaluate_signatures(FRAMEWORK_SIGNATURES)
        # check cdns
        self._evaluate_signatures(CDN_SIGNATURES)
        # check databases
        self._evaluate_signatures(DATABASE_SIGNATURES)
        # check load balancers
        self._evaluate_signatures(LOAD_BALANCER_SIGNATURES)

        #a way to build our repo of systems
        self._log_unmatched_tech()

        # merge external data
        self.merge_with_nmap()
        self.merge_with_tls()

        # save telemetry
        self._write_telemetry_file()

        return self.export()

    def collect_http_data(self) -> None:
        """
        Retrieves HTTP information from the target and builds the cache.
        """
        try:

            response = requests.get \
            (
                self.target_url,
                timeout=10,
                verify=False,
            )

            self.cache["status_code"] = response.status_code
            self.cache["final_url"] = response.url

            headers = {}
            for key, value in response.headers.items():
                headers[key.lower()] = str(value).lower()
            self.cache["headers"] = headers

            cookies: dict[str, str] = {}
            cookie_dict = response.cookies.get_dict()
            for cookie_name, cookie_value in cookie_dict.items():
                if cookie_name is None:
                    continue

                cookies[cookie_name.lower()] = \
                (
                    "" if cookie_value is None else str(cookie_value).lower()
                )
            self.cache["cookies"] = cookies

            self.cache["html_text"] = response.text.lower()

            soup = BeautifulSoup \
            (
                response.text,
        "html.parser",
            )

            if soup.title and soup.title.string:
                self.cache["title"] = soup.title.string.lower()

            self.cache["meta_tags"] = soup.find_all("meta")

            scripts = []
            for script in soup.find_all("script"):
                source = script.get("src")
                if source:
                    scripts.append(str(source).lower())
            self.cache["scripts"] = scripts

            links = []
            for link in soup.find_all("link"):
                href = link.get("href")
                if href:
                    links.append(str(href).lower())
            self.cache["links"] = links

        except Exception as error:

            logger.warning \
            (
                f"[Fingerprint] Failed collecting HTTP data: {error}"
            )

    #checks against our signature files and determines if it's a "known" technology
    def _evaluate_signatures(self, signature_dictionary: dict) -> None:

        for tech_name, rules in signature_dictionary.items():

            category = rules.get("category")
            vendor = rules.get("vendor")

            product = rules.get \
            (
                "product",
                tech_name.lower(),
            )

            version = self._extract_version(rules)

            # check headers
            for rule in rules.get("headers", []):

                if len(rule) == 3:
                    header_key = rule[0]
                    expected_value = rule[1]
                    weight = rule[2]
                else:
                    header_key = rule[0]
                    expected_value = ""
                    weight = rule[1]

                header_value = self.cache["headers"].get(header_key.lower())

                if header_value is None:
                    continue

                if not expected_value or expected_value.lower() in header_value:
                        self._add_software \
                        (
                            category=category,
                            vendor=vendor,
                            product=product,
                            version=version,
                            weight=weight,
                            source="header",
                        )

            # check cookies
            for rule in rules.get("cookies", []):

                if len(rule) == 3:
                    cookie_key = rule[0]
                    expected_value = rule[1]
                    weight = rule[2]
                else:
                    cookie_key = rule[0]
                    expected_value = ""
                    weight = rule[1]

                cookie_value = self.cache["cookies"].get(cookie_key.lower())

                if cookie_value is not None:
                    if not expected_value or expected_value.lower() in cookie_value:
                        self._add_software \
                        (
                            category=category,
                            vendor=vendor,
                            product=product,
                            version=version,
                            weight=weight,
                            source="cookie",
                        )

            # check meta tags
            for rule in rules.get("meta", []):

                expected_value = rule[0]
                weight = rule[1]

                for tag in self.cache["meta_tags"]:

                    tag_content = str(tag.get("content", "")).lower()

                    if expected_value.lower() in tag_content:
                        self._add_software \
                        (
                            category=category,
                            vendor=vendor,
                            product=product,
                            version=version,
                            weight=weight,
                            source="meta",
                        )

            # check scripts
            for rule in rules.get("scripts", []):

                expected_value = rule[0]
                weight = rule[1]

                for script in self.cache["scripts"]:

                    if expected_value.lower() in script:
                        self._add_software \
                        (
                            category=category,
                            vendor=vendor,
                            product=product,
                            version=version,
                            weight=weight,
                            source="script",
                        )
    #method of extracting version
    def _extract_version(self, rules: JSONDict) -> str | None:

        for extractor in rules.get("version_extractors", []):

            extractor_type = extractor.get("type")
            target = extractor.get("target", "").lower()
            regex_pattern = extractor.get("regex", "")

            if extractor_type == "header":

                header_value = self.cache["headers"].get(target)

                if header_value:

                    match = re.search\
                    (
                        regex_pattern,
                        header_value,
                        re.IGNORECASE,
                    )

                    if match:
                        return match.group(1)

            elif extractor_type == "meta":

                for tag in self.cache["meta_tags"]:

                    tag_name = str(
                            tag.get("name")
                            or tag.get("property")
                            or ""
                    ).lower()

                    if tag_name == target:

                        tag_content = str(tag.get("content", ""))

                        match = re.search \
                        (
                            regex_pattern,
                            tag_content,
                            re.IGNORECASE,
                        )

                        if match:
                            return match.group(1)

        return None

    #merge fingerprint data with Nmap service information
    def merge_with_nmap(self) -> None:

        for port in self.nmap_data.get("ports", []):

            port_product = port.get("product", "")

            for software in self.discovered.values():

                software_product = software["product"].lower()
                nmap_product = port_product.lower()

                if \
                (
                        nmap_product in software_product
                        or software_product in nmap_product
                ):
                    self._add_software \
                    (
                        category=software["category"],
                        vendor=software["vendor"],
                        product=software["product"],
                        version=port.get("version"),
                        weight=25,
                        source="nmap",
                    )
                    return

            if port_product:
                self._add_software \
                (
                    category="service",
                    vendor="unknown",
                    product=port_product.lower(),
                    version=port.get("version"),
                    weight=85,
                    source="nmap",
                )

    #merge tls certs
    def merge_with_tls(self) -> None:

        try:

            targets = self.tls_data.get("targets", [{}])
            certificate = targets[0].get("certificate", {})

            issuer_name = certificate.get("issuer", {}).get("organizationName", "").lower()

            if "cloudflare" in issuer_name:
                self._add_software \
                (
                    category="cdn",
                    vendor="cloudflare",
                    product="cloudflare",
                    version=None,
                    weight=60,
                    source="tls",
                )


        except Exception as error:
            logger.debug(f"[Fingerprint] TLS merge skipped: {error}")

    def _add_software \
    (
                self,
                category: str,
                vendor: str,
                product: str,
                version: str | None,
                weight: int,
                source: str,
    ) -> None:

        software_key = f"{vendor}_{product}".lower()

        if software_key in self.discovered:

            software = self.discovered[software_key]

            software["evidence_score"] = min \
            (
                software["evidence_score"] + weight,
                100,
            )

            if source not in software["sources"]:
                software["sources"].append(source)

            if version and not software["version"]:
                software["version"] = version

        else:

            self.discovered[software_key] = \
            {
                "category": category,
                "vendor": vendor,
                "product": product,
                "version": version,
                "evidence_score": min(weight, 100),
                "sources": [source],
            }

    #logs servers that are not in the signature folders so we can use that info
    # to improve our signature db
    def _log_unmatched_tech(self) -> None:

        server_header = self.cache["headers"].get("server")

        if server_header:

            has_web_server = False

            for software in self.discovered.values():
                if software["category"] == "web_server":
                    has_web_server = True
                    break

            if not has_web_server:
                self.telemetry["unknown_server_strings"].append(server_header)

    def export(self) -> JSONDict:

        for software in self.discovered.values():

            score = software["evidence_score"]

            if score >= 90:
                confidence = "high"
            elif score >= 60:
                confidence = "medium"
            else:
                confidence = "low"

            software["confidence"] = confidence

        result = \
        {
            "target": self.target_url,
            "fingerprint":
            {
                "software": list(self.discovered.values()),
            },
            "telemetry": self.telemetry,
        }

        return result

    #this is temporary, we can write to the db in the future and remove the temp file
    def _write_telemetry_file(self) -> None:
        output_file = Path(__file__).resolve().parents[2] / "unknown_telemetry.txt"
        with output_file.open("a", encoding="utf-8") as file:

            file.write("=" * 80 + "\n")
            file.write(f"Target: {self.target_url}\n\n")

            for category, values in self.telemetry.items():

                if not values:
                    continue

                file.write(f"[{category}]\n")

                unique_values = sorted(set(values))

                for value in unique_values:
                    file.write(f"  - {value}\n")

                file.write("\n")