import io
import os
import tempfile
from pathlib import Path
from typing import Any
from uuid import UUID

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from PIL import Image

MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 16_000_000


def checked_png(contents: bytes) -> bytes:
    if not 0 < len(contents) <= MAX_IMAGE_BYTES:
        raise ValueError("Invalid report image size")

    with Image.open(io.BytesIO(contents)) as image:
        if (
            image.format != "PNG"
            or image.width * image.height > MAX_PIXELS
        ):
            raise ValueError("Invalid report image")

        image.verify()

    with Image.open(io.BytesIO(contents)) as image:
        image.load()
        output = io.BytesIO()
        normalized = image.convert("RGBA")
        normalized.info.clear()
        normalized.save(output, format="PNG")

    value = output.getvalue()

    if len(value) > MAX_IMAGE_BYTES:
        raise ValueError("Report image exceeds size limit")

    return value


def screenshot_path(scan_id: str) -> Path:
    root = Path(
        os.getenv(
            "SCREENSHOT_OUTPUT_DIR",
            "/app/generated_reports/screenshots",
        )
    ).resolve()

    path = root / f"{UUID(scan_id)}.png"

    if path.is_symlink() or path.resolve().parent != root:
        raise ValueError("Invalid screenshot path")

    if path.exists() and not path.is_file():
        raise ValueError("Invalid screenshot file")

    return path


def screenshot_client() -> Any:
    return boto3.client(
        "s3",
        region_name=os.getenv("AWS_REGION", "af-south-1"),
        config=Config(
            connect_timeout=5,
            read_timeout=15,
            retries={"max_attempts": 2},
        ),
    )


def screenshot_bucket() -> str:
    bucket = os.environ.get("REPORT_S3_BUCKET", "")

    if not bucket:
        raise RuntimeError("Report bucket is not configured")

    return bucket


def save_screenshot(scan_id: str, contents: bytes) -> str:
    scan_id = str(UUID(scan_id))
    contents = checked_png(contents)
    mode = os.getenv("REPORT_STORAGE", "local").lower()

    if mode == "s3":
        screenshot_client().put_object(
            Bucket=screenshot_bucket(),
            Key=f"screenshots/{scan_id}.png",
            Body=contents,
            ContentType="image/png",
            ServerSideEncryption="AES256",
        )

    elif mode == "local":
        path = screenshot_path(scan_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None

        try:
            with tempfile.NamedTemporaryFile(
                dir=path.parent,
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(contents)

            os.replace(temporary, path)

        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    else:
        raise ValueError("Invalid report storage mode")

    return "scan-screenshot.png"


def load_screenshot(scan_id: str) -> bytes | None:
    scan_id = str(UUID(scan_id))
    mode = os.getenv("REPORT_STORAGE", "local").lower()

    if mode == "s3":
        try:
            result = screenshot_client().get_object(
                Bucket=screenshot_bucket(),
                Key=f"screenshots/{scan_id}.png",
            )

        except ClientError as exc:
            if exc.response["Error"]["Code"] in {
                "NoSuchKey",
                "404",
                "NotFound",
            }:
                return None

            raise

        body = result["Body"]

        try:
            contents = body.read(MAX_IMAGE_BYTES + 1)
        finally:
            body.close()

    elif mode == "local":
        try:
            with screenshot_path(scan_id).open("rb") as handle:
                contents = handle.read(MAX_IMAGE_BYTES + 1)

        except FileNotFoundError:
            return None

    else:
        raise ValueError("Invalid report storage mode")

    return checked_png(contents)