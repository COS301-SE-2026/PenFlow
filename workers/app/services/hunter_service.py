import logging

# Logger to track this specific worker
logger = logging.getLogger(__name__)

def normalize_hunter_data(rawData: dict) -> dict:
    """
    Extracts email formats and employee addresses from raw Hunter.io JSON.
    Strips superfluous info so we only get a list of targets to process.
    """
    logger.info("Normalizing Hunter.io data:")
    
    # Hunter.io wraps their actual payload inside a "data" key in accordance to their documentation
    dataBlock = rawData.get("data", {})
    
    # Extract the email pattern so pentesting tools can guess other emails
    pattern = dataBlock.get("pattern", "Unknown")
    
    # Safely get the list of emails
    rawEmails = dataBlock.get("emails", [])
    formattedEmails = []

    # Iterate through each employee entry
    for emp in rawEmails:
        # We only care about the email, type, and confidence score.
        # We intentionally ignore the rest of the marketing metadata to save DB space.
        emailAddress = emp.get("value", "Unknown")
        emailType = emp.get("type", "Unknown")
        confidence = emp.get("confidence", 0)

        # Skip entries that are completely broken
        if emailAddress == "Unknown":
            continue

        emailObj = \
        {
            "email": emailAddress,
            "type": emailType,
            "confidence_score": confidence
        }
        
        formattedEmails.append(emailObj)

    # Our strict data contract schema format for the Phishing Surface section
    final_result = \
    {
        "provider": "Hunter.io",
        "email_format_pattern": pattern,
        "public_emails_found": formattedEmails
    }

    return final_result