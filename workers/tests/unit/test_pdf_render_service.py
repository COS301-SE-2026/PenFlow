import importlib.util
import io
import os
import socket
import subprocess
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image

from app.services import pdf_assets
from app.services import pdf_render_service as service
from app.services.pdf_renderer_child import (
    BASE_URL,
    ResourceGuard,
    render,
)


@pytest.fixture
def assets():
    return {
        name: (service.TEMPLATE_DIR / name).read_bytes()
        for name in (
            "report_styles.css",
            "bluevision_logo.png",
            "brocode_logo.png",
        )
    }


def png_bytes():
    image = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(image, format="PNG")
    return image.getvalue()


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://169.254.169.254/",
        "http://[::1]/",
        "https://example.com/",
        "file:///etc/passwd",
        "file:///proc/self/environ",
        "data:image/svg+xml,<svg/>",
        BASE_URL + "../private.txt",
        BASE_URL + "%2e%2e/private.txt",
        BASE_URL + "other-client.png",
    ],
)
def test_rejects_resource(url, assets):
    guard = ResourceGuard(assets)

    with pytest.raises(ValueError):
        guard(url)

    assert guard.denied


def test_approved_assets(assets):
    guard = ResourceGuard(assets)

    result = guard(BASE_URL + "report_styles.css")
    assert result["mime_type"] == "text/css"


@pytest.mark.parametrize(
    "body",
    [
        '<img src="http://169.254.169.254/">',
        '<style>@import "https://evil.example/a.css";</style>',
        '<svg><image href="https://evil.example/a.png" /></svg>',
        '<link rel="attachment" href="file:///etc/passwd">',
    ],
)
def test_blocked_fetch_prevents_publication(
    body,
    assets,
    tmp_path,
    monkeypatch,
):
    connect = Mock(
        side_effect=AssertionError("Network access attempted")
    )
    monkeypatch.setattr(socket, "create_connection", connect)

    output = tmp_path / "blocked.pdf"

    with pytest.raises(ValueError, match="prohibited"):
        render(body, assets, output)

    assert not output.exists()
    connect.assert_not_called()


def test_scoped_screenshots(tmp_path, monkeypatch):
    monkeypatch.setenv("REPORT_STORAGE", "local")
    monkeypatch.setenv("SCREENSHOT_OUTPUT_DIR", str(tmp_path))

    scan_a = str(uuid4())
    scan_b = str(uuid4())

    assert pdf_assets.save_screenshot(
        scan_a,
        png_bytes(),
    ) == "scan-screenshot.png"

    assert pdf_assets.load_screenshot(scan_a)
    assert pdf_assets.load_screenshot(scan_b) is None


def test_subprocess_render(tmp_path, monkeypatch):
    monkeypatch.setenv("REPORT_OUTPUT_DIR", str(tmp_path))

    result = service.generate_pdf_from_html(
        "<p>Report</p>",
        report_id=str(uuid4()),
    )

    assert result.read_bytes().startswith(b"%PDF-")


def test_failed_child_never_publishes(tmp_path, monkeypatch):
    monkeypatch.setenv("REPORT_OUTPUT_DIR", str(tmp_path))

    with pytest.raises(RuntimeError):
        service.generate_pdf_from_html(
            '<img src="file:///etc/passwd">',
            report_id=str(uuid4()),
        )

    assert not list(tmp_path.glob("*.pdf"))
    assert not list(tmp_path.glob(".pdf-*"))


@pytest.mark.parametrize(
    "report_type",
    ["passive", "phase2", "phase3"],
)
def test_actual_templates(report_type, tmp_path, monkeypatch):
    repo = Path(__file__).resolve().parents[3]
    fixtures = Path(
        os.getenv(
            "REPORT_TEST_FIXTURES",
            str(repo / "backend" / "app"),
        )
    )

    environment = Environment(
        loader=FileSystemLoader(str(fixtures / "templates")),
        autoescape=select_autoescape(["html"]),
    )

    scan = {
        "id": str(uuid4()),
        "domain": "example.com",
        "status": "completed",
    }

    if report_type in {"passive", "phase2"}:
        filename = (
            "report_context.py"
            if report_type == "passive"
            else "phase2_report_context.py"
        )

        spec = importlib.util.spec_from_file_location(
            "test_context_" + report_type,
            fixtures / "utils" / filename,
        )
        assert spec is not None
        assert spec.loader is not None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if report_type == "passive":
            context = module.build_report_context(scan, [], [])
            context["reputation"]["screenshot_path"] = "brocode_logo.png"
            template = "passive_report_template.html"

        else:
            context = module.build_phase2_report_context(
                scan, [], [], [], [], [],
            )
            template = "phase2_report_template.html"

    else:
        context = {
            "engagement": {"id": scan["id"]},
            "engagement_title": "Test",
            "engagement_type": "black_box",
            "assessment_type": "web",
            "client": "Test client",
            "findings": [],
            "assets": [],
            "severity_counts": dict.fromkeys(
                ["critical", "high", "medium", "low", "info"],
                0,
            ),
            "total_findings": 0,
            "report_version": 1,
        }
        template = "phase3_report_template.html"

    html = environment.get_template(template).render(**context)

    monkeypatch.setenv("REPORT_OUTPUT_DIR", str(tmp_path))

    result = service.generate_pdf_from_html(
        html,
        report_id=scan["id"],
        kind="engagement" if report_type == "phase3" else "scan",
    )

    assert result.read_bytes().startswith(b"%PDF-")


def test_timeout_cleanup(tmp_path, monkeypatch):
    monkeypatch.setenv("REPORT_OUTPUT_DIR", str(tmp_path))

    def timeout(command, **kwargs):
        Path(command[-1]).write_bytes(b"%PDF-partial")
        raise subprocess.TimeoutExpired(command, 120)

    monkeypatch.setattr(service.subprocess, "run", timeout)

    with pytest.raises(RuntimeError):
        service.generate_pdf_from_html(
            "<p>Report</p>",
            report_id=str(uuid4()),
        )

    assert not list(tmp_path.iterdir())


def test_invalid_output_id(tmp_path, monkeypatch):
    monkeypatch.setenv("REPORT_OUTPUT_DIR", str(tmp_path))

    with pytest.raises(ValueError):
        service.generate_pdf_from_html(
            "<p>Report</p>",
            report_id="../../etc/passwd",
        )

    assert not list(tmp_path.iterdir())


def test_screenshot_symlink_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("REPORT_STORAGE", "local")
    monkeypatch.setenv("SCREENSHOT_OUTPUT_DIR", str(tmp_path))

    scan_id = str(uuid4())
    (tmp_path / f"{scan_id}.png").symlink_to("/etc/passwd")

    with pytest.raises(ValueError):
        pdf_assets.load_screenshot(scan_id)


def test_s3_scope(monkeypatch):
    monkeypatch.setenv("REPORT_STORAGE", "s3")
    monkeypatch.setenv("REPORT_S3_BUCKET", "private-reports")

    client = Mock()
    client.get_object.return_value = {
        "Body": io.BytesIO(png_bytes()),
    }
    monkeypatch.setattr(
        pdf_assets,
        "screenshot_client",
        lambda: client,
    )

    scan_id = str(uuid4())

    assert pdf_assets.save_screenshot(
        scan_id,
        png_bytes(),
    ) == "scan-screenshot.png"

    assert (
        client.put_object.call_args.kwargs["Key"]
        == f"screenshots/{scan_id}.png"
    )
    assert pdf_assets.load_screenshot(scan_id)

    client.get_object.assert_called_once_with(
        Bucket="private-reports",
        Key=f"screenshots/{scan_id}.png",
    )


@pytest.mark.parametrize("engagement", [False, True])
def test_failed_task_never_stores_pdf(monkeypatch, engagement):
    from app.tasks import report_tasks as tasks

    monkeypatch.setattr(
        tasks,
        "generate_pdf_from_html",
        Mock(side_effect=RuntimeError("blocked")),
    )

    store = Mock()
    callback = Mock()

    if engagement:
        monkeypatch.setattr(
            tasks.ReportStorageService,
            "store_engagement_report",
            store,
        )
        monkeypatch.setattr(
            tasks,
            "send_engagement_report_callback",
            callback,
        )

        result = tasks.render_engagement_report_pdf_task(
            str(uuid4()),
            1,
            "<p>Report</p>",
            "/untrusted/report.pdf",
        )

    else:
        monkeypatch.setattr(
            tasks.ReportStorageService,
            "store_report",
            store,
        )
        monkeypatch.setattr(
            tasks,
            "send_report_callback",
            callback,
        )

        result = tasks.render_report_pdf_task(
            str(uuid4()),
            "<p>Report</p>",
            "/untrusted/report.pdf",
        )

    assert result["status"] == "failed"
    store.assert_not_called()
    assert callback.call_args.kwargs["status"] == "failed"


def test_repeated_resource_limit():
    guard = ResourceGuard({"report_styles.css": b"p{}"})

    for _ in range(100):
        guard(BASE_URL + "report_styles.css")

    with pytest.raises(ValueError):
        guard(BASE_URL + "report_styles.css")

    assert guard.denied


def test_oversize_html_rejected_before_child(tmp_path, monkeypatch):
    monkeypatch.setenv("REPORT_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(service, "MAX_HTML_BYTES", 4)

    process = Mock()
    monkeypatch.setattr(service.subprocess, "run", process)

    with pytest.raises(ValueError):
        service.generate_pdf_from_html(
            "<p>Oversize</p>",
            report_id=str(uuid4()),
        )

    process.assert_not_called()


def test_image_dimensions_bounded(monkeypatch):
    monkeypatch.setattr(pdf_assets, "MAX_PIXELS", 1)

    with pytest.raises(ValueError):
        pdf_assets.checked_png(png_bytes())