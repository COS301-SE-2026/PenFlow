import logging

import dns.exception
import dns.resolver

logger = logging.getLogger(__name__)


def verify_txt_record(domain: str, verification_token: str) -> bool:
    """
    Verify that the supplied verification token exists
    in one of the domain's DNS TXT records.

    Returns:
        True if the verification token is found.
        False if it's not found nor not matching what we may expect.
    """

    logger.info(
        f"[Domain Verification] Checking TXT records for the domain: {domain}"
    )

    try:
        answers = dns.resolver.resolve(domain, "TXT")

        for rdata in answers:
            txt_record = rdata.to_text().strip('"')

            if verification_token in txt_record:
                logger.info(
                    f"[Domain Verification] Verification succeeded for the domain: {domain}"
                )
                return True

        logger.info(
            f"[Domain Verification] Verification token not found for the domain: {domain}"
        )
        return False

    except (
        dns.resolver.NoAnswer,
        dns.resolver.NXDOMAIN,
        dns.resolver.NoNameservers,
        dns.exception.Timeout,
    ) as excep:

        logger.warning(
            f"[Domain Verification] DNS lookup failed for the domain: {domain}: {excep}"
        )
        return False

    except Exception:
        logger.exception(
            f"[Domain Verification] Unexpected verification error for the domain: {domain}"
        )
        return False