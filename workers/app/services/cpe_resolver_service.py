import logging
from typing import Any

logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]

#Maps software names from the fingerprint worker
#to official NVD vendor/product names.
#will probably extend over time
KNOWN_PRODUCTS = {
    "apache httpd": \
    {
        "vendor": "apache",
        "product": "http_server",
    },
    "nginx": \
    {
        "vendor": "nginx",
        "product": "nginx",
    },
    "openssl": \
    {
        "vendor": "openssl",
        "product": "openssl",
    },
    "openssh": \
    {
        "vendor": "openbsd",
        "product": "openssh",
    },
    "tomcat": \
    {
        "vendor": "apache",
        "product": "tomcat",
    },
    "mysql": \
    {
        "vendor": "oracle",
        "product": "mysql",
    },
    "postgresql": \
    {
        "vendor": "postgresql",
        "product": "postgresql",
    },
}

class CPEResolverService:
    def __init__(self, software_inventory: list[JSONDict]):
        self.software_inventory = software_inventory

    def run(self) -> list[JSONDict]:
        logger.info(
            "[CPE_Resolver] Resolving %s software objects.",
            len(self.software_inventory),
        )

        resolved_inventory = []

        for software in self.software_inventory:
            product_name = software.get("product", "").strip().lower()
            version = software.get("version")

            # Fingerprinting sometimes reports Tomcat as 1.1. as it is the wrappers version
            # not the underlying service, we ignore it for now till we
            # implement better version probing later
            if not version:
                version = "*"
            else:
                version = version.strip()

                if version in ("", "unknown", "1.1"):
                    version = "*"

            mapping = KNOWN_PRODUCTS.get(product_name)

            if mapping is None:
                logger.warning\
                (
                    "[CPE_Resolver] No CPE mapping exists for '%s'",
                    product_name,
                )
                continue
            resolved = software.copy()
            vendor = mapping["vendor"]
            product = mapping["product"]
            resolved["vendor"] = vendor
            resolved["product"] = product
            resolved["cpe"] = f"cpe:2.3:a:{vendor}:{product}:{version}:*:*:*:*:*:*:*"
            resolved_inventory.append(resolved)

        return resolved_inventory


def run_cpe_resolution(
    software_inventory: list[JSONDict],
) -> list[JSONDict]:
    return CPEResolverService(software_inventory).run()
