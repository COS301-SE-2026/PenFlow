import logging

# Logger to track this specific worker
logger = logging.getLogger(__name__)

def normalize_urlscan_data(rawData: dict) -> dict:
    """
    Extracts reputation flags and screenshot paths from a full URLScan Result(Will modify to save imgs to db for report history at a later date).
    """
    logger.info("Normalizing URLScan data (Production Mode):")
    
    # Extract the UUID from the Task block (unique Key for the report)
    task = rawData.get("task", {})
    uuid = task.get("uuid", "Unknown")
    
    # Extract Malicious Flags from the Verdicts block
    verdicts = rawData.get("verdicts", {})
    engines = verdicts.get("engines", {})
    
    # Safety: Default to 0 if the 'malicious' key is missing in the raw JSON
    maliciousCount = engines.get("malicious", 0)

    # Construct the Screenshot URL for the PDF report
    # If the API doesn't provide a direct link, we can build it via the UUID.
    screenshotUrl = "N/A"
    if uuid != "Unknown":
        screenshotUrl = f"https://urlscan.io/screenshots/{uuid}.png"

    # Our strict data contract schema format for the Reputation section
    final_result = \
    {
        "provider": "URLScan",
        "malicious_flags": maliciousCount,
        "urlscan_uuid": uuid,
        "screenshot_url": screenshotUrl
    }

    return final_result