import os 
from pathlib import Path
import boto3
from botocore.exceptions import BotoCoreError, ClientError

REPORT_STORAGE = os.getenv("REPORT_STORAGE", "local").lower()
REPORT_OUTPUT_DIR = Path(os.getenv("REPORT_OUTPUT_DIR", "/app/generated_reports"))
REPORT_S3_BUCKET = os.getenv("REPORT_S3_BUCKET")
AWS_REGION = os.getenv("AWS_REGION", "af-south-1")


class ReportStorageService:

    @staticmethod
    def get_local_report_storage(storage_ref: str) -> Path:
        if REPORT_STORAGE != "local":
            raise Exception("Local report path requested while storage mode is not local")

        path = Path(storage_ref)
        if not path.exists():
            raise Exception(f"Report does not exist: {storage_ref}")

        return path


    @staticmethod
    def get_s3_object(storage_ref: str) -> dict:
        if REPORT_STORAGE != "s3":
            raise Exception("S3 report requested while storage mode is not s3")

        if not REPORT_S3_BUCKET:
            raise Exception("S3 bucket is not configured")

        try:
            client = boto3.client("s3", region_name=AWS_REGION)
            return client.get_object(Bucket=REPORT_S3_BUCKET, Key=storage_ref)

        except(BotoCoreError, ClientError) as err:
            raise Exception(f"Failed to retrieve report from S3: {storage_ref}") from err


    @staticmethod
    def report_exists(storage_ref: str) -> bool:
        if REPORT_STORAGE == "local":
            return Path(storage_ref).exists()

        if REPORT_STORAGE == "s3":
            if not REPORT_S3_BUCKET:
                return False

            try:
                client = boto3.client("s3", region_name=AWS_REGION)
                client.head_object(Bucket=REPORT_S3_BUCKET, Key=storage_ref)
                return True

            except (BotoCoreError, ClientError):
                return False

        raise Exception(f"Unsupported REPORT_STORAGE mode: {REPORT_STORAGE}")


    @staticmethod
    def is_local() -> bool:
        return REPORT_STORAGE == "local"


    @staticmethod
    def is_s3() -> bool:
        return REPORT_STORAGE == "s3"