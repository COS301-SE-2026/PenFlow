import os
from pathlib import Path
import boto3
from botocore.exceptions import BotoCoreError, ClientError

REPORT_STORAGE = os.getenv("REPORT_STORAGE", "local").lower()
REPORT_S3_BUCKET = os.getenv("REPORT_S3_BUCKET")
AWS_REGION = os.getenv("AWS_REGION", "af-south-1")

class ReportStorageService:

    @staticmethod
    def store_report(local_path: str | Path, scan_id: str) -> str:
        path = Path(local_path)

        if not path.exists():
            raise Exception(f"Report does not exist: {path}")

        if REPORT_STORAGE == "local":
            return str(path)

        if REPORT_STORAGE == "s3":
            if not REPORT_S3_BUCKET:
                raise Exception("S3 Bucket is not configured.")

            storage_key = f"reports/{scan_id}/report.pdf"

            try:
                client = boto3.client("s3", region_name=AWS_REGION)
                client.upload_file(
                    Filename=str(path),
                    Bucket=REPORT_S3_BUCKET,
                    Key=storage_key,
                    ExtraArgs={"Content-Type": "application/pdf"},
                )

            except (BotoCoreError, ClientError) as err:
                raise Exception(f"Failed to upload report to S3: {storage_key}") from err

            
            return storage_key

        raise Exception(f"Unsupported REPORT_STORAGE mode: {REPORT_STORAGE}")