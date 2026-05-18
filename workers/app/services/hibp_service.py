import logging

logger = logging.getLogger(__name__)

def normalize_hibp_data(raw_data: list) -> dict:
    """
    Normalizes breach data from a raw HaveIBeenPwned response payload.
    """
    logger.info("Normalizing HIBP breach data:")
    
    unique_breaches = set()
    
    for breach in raw_data:
        breach_name = breach.get("Name", "Unknown")
        unique_breaches.add(breach_name)

    final_breach_list = sorted(list(unique_breaches))

    # Strict data contract format required by the database layer
    final_result = {
        "provider": "HaveIBeenPwned",
        "pwned_accounts_count": len(final_breach_list),
        "known_breaches": final_breach_list
    }

    return final_result