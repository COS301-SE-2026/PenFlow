import logging
from typing import Any

from app.queue.celery_app import celery_app
from app.services.domain_verification_service import verify_txt_record
from app.utils.callback import send_source_callback

# same logger implementation as what we have been using.
logger = logging.getLogger(__name__)

JSONDict = dict[str, Any]


@celery_app.task(name="scan.domain_verification")
def run_domain_verification_task(
        scan_id: str,
        domain: str,
        verification_token: str,
) -> JSONDict:
    """
    Verifies that a domain owner has published the expected TXT record token we generated.

    This worker perfomrs verification of token we supply.
    The backend remains responsible for:
    Generating the token and storing it in the DB.
    """

    logger.info(f"[Domain Verification] Verifying ownership of the domain: {domain}")

    try:
        verified = verify_txt_record(domain, verification_token)
        # If we want to do retry logic we can add it here later:
        # We can implement exponential backoff retry logic but that would fail if the user
        # doesnt add the token as instructed.

        result = {
            "scan_id": scan_id,
            "source_name": "domain_verification",
            "status": "completed",
            "raw_result": {
                "domain": domain,
                "verified": verified,
            },
            # no findings or assets for verificaton.
            "findings": [],
            "assets": [],
        }

    except Exception as error:
        logger.exception(
            f"[Domain Verification] Worker failed while verifying the domain: {domain}"
        )

        result = {
            "scan_id": scan_id,
            "source_name": "domain_verification",
            "status": "failed",
            "raw_result": {
                "error": str(error),
            },
            "findings": [],
            "assets": [],
            "error_message": str(error),
        }

    #
    send_source_callback(
        scan_id=scan_id,
        source_name=result["source_name"],
        status=result["status"],
        raw_result=result["raw_result"],
        findings=result["findings"],
        assets=result["assets"],
        error_message=result.get("error_message"),
    )

    return result