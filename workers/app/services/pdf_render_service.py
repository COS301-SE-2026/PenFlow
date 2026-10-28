import base64
import fcntl
import json
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

from app.services.pdf_assets import checked_png, load_screenshot

BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = BASE_DIR / "templates"
MAX_HTML_BYTES = 4 * 1024 * 1024


@contextmanager
def render_slot() -> Iterator[None]:
    descriptor = os.open(
        "/tmp/penflow-pdf-render.lock",
        os.O_WRONLY
        | os.O_CREAT
        | os.O_NOFOLLOW
        | os.O_NONBLOCK,
        0o600,
    )

    with os.fdopen(descriptor, "a") as handle:
        deadline = time.monotonic() + 120

        while True:
            try:
                fcntl.flock(
                    handle,
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                )
                break

            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        "PDF renderer is busy"
                    ) from None

                time.sleep(0.1)

        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def generate_pdf_from_html(
        html_content: str,
        *,
        report_id: str,
        kind: str = "scan",
        version: int = 1,
        include_screenshot: bool = False,
) -> Path:
    report_id = str(UUID(report_id))

    if (
        kind not in {"scan", "engagement"}
        or type(include_screenshot) is not bool
    ):
        raise ValueError("Invalid report scope")

    if (
        type(version) is not int
        or not 1 <= version <= 1_000_000
    ):
        raise ValueError("Invalid report version")

    if kind != "scan" and include_screenshot:
        raise ValueError("Invalid screenshot scope")

    if len(html_content.encode("utf-8")) > MAX_HTML_BYTES:
        raise ValueError("Report HTML exceeds size limit")

    root = Path(
        os.getenv(
            "REPORT_OUTPUT_DIR",
            str(BASE_DIR.parent / "generated_reports"),
        )
    ).resolve()
    root.mkdir(parents=True, exist_ok=True)

    filename = (
        f"penflow_report_{report_id}.pdf"
        if kind == "scan"
        else f"engagement_report_{report_id}_v{version}.pdf"
    )
    output = root / filename

    if output.is_symlink():
        raise ValueError("Invalid report output path")

    with render_slot():
        assets: dict[str, bytes] = {}

        for name in (
            "report_styles.css",
            "bluevision_logo.png",
            "brocode_logo.png",
        ):
            path = TEMPLATE_DIR / name

            if (
                path.is_symlink()
                or path.resolve().parent != TEMPLATE_DIR.resolve()
            ):
                raise ValueError("Invalid bundled report asset")

            with path.open("rb") as handle:
                value = handle.read(2 * 1024 * 1024 + 1)

            if len(value) > 2 * 1024 * 1024:
                raise ValueError(
                    "Bundled report asset exceeds size limit"
                )

            assets[name] = (
                checked_png(value)
                if name.endswith(".png")
                else value
            )

        if include_screenshot:
            assets["scan-screenshot.png"] = (
                load_screenshot(report_id)
                or assets["brocode_logo.png"]
            )

        payload = json.dumps({
            "html": html_content,
            "assets": {
                name: base64.b64encode(value).decode("ascii")
                for name, value in assets.items()
            },
        }).encode("utf-8")

        if len(payload) > 40 * 1024 * 1024:
            raise ValueError(
                "Report payload exceeds size limit"
            )

        with tempfile.TemporaryDirectory(
            prefix=".pdf-",
            dir=root,
        ) as directory:
            temporary = Path(directory) / "report.pdf"

            environment = {
                "PATH": os.defpath,
                "LANG": "C.UTF-8",
                "HOME": directory,
                "TMPDIR": directory,
                "PYTHONDONTWRITEBYTECODE": "1",
            }

            try:
                subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "app.services.pdf_renderer_child",
                        str(temporary),
                    ],
                    input=payload,
                    cwd=BASE_DIR.parent,
                    env=environment,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=120,
                    check=True,
                )

            except (
                subprocess.CalledProcessError,
                subprocess.TimeoutExpired,
            ) as exc:
                raise RuntimeError(
                    "PDF rendering failed or exceeded its limits"
                ) from exc

            if (
                temporary.is_symlink()
                or not temporary.is_file()
                or temporary.stat().st_size > 32 * 1024 * 1024
            ):
                raise ValueError("Invalid generated PDF")

            with temporary.open("rb") as handle:
                if handle.read(5) != b"%PDF-":
                    raise ValueError("Invalid generated PDF")

            os.replace(temporary, output)


    return output