import logging
from typing import Any

logger = logging.getLogger(__name__)
JSONDict = dict[str, Any]


class CPEResolverService:
    def __init__(self, software_inventory: list[JSONDict]):
        self.software_inventory = software_inventory

    def run(self) -> list[JSONDict]:
        logger.info\
        (
            "[CPE_Resolver] Resolving %s software objects.",
            len(self.software_inventory),
        )

        resolved_inventory = []

        for software in self.software_inventory:
            vendor = software.get("vendor", "unknown")
            product = software.get("product", "unknown")
            version = software.get("version") or "*"

            # Fingerprinting sometimes reports Tomcat as 1.1. as it is the wrappers version
            # not the underlying service, we ignore it for now till we
            # implement better version probing later
            if product == "tomcat" and version == "1.1":
                version = "*"

            software["cpe"] = \
            (
                f"cpe:2.3:a:{vendor}:{product}:{version}:*:*:*:*:*:*:*"
            )

            resolved_inventory.append(software)

        return resolved_inventory


def run_cpe_resolution\
(
    software_inventory: list[JSONDict],
) -> list[JSONDict]:
    return CPEResolverService(software_inventory).run()