import pytest

from app.models.base import ScanType
from app.services.report_service import prepare_report_assets


@pytest.mark.parametrize(
    "reference",
    [
        "file:///etc/passwd",
        "/app/generated_reports/screenshots/other.png",
        "https://evil.example/image.png",
        "default.png",
        None,
    ],
)
def test_untrusted_screenshot_reference(reference):
    context = {
        "reputation": {"screenshot_path": reference},
    }

    assert not prepare_report_assets(
        context,
        ScanType.PASSIVE_CTEM,
    )
    assert (
        context["reputation"]["screenshot_path"]
        == "brocode_logo.png"
    )


def test_approved_screenshot_token():
    context = {
        "reputation": {
            "screenshot_path": "scan-screenshot.png",
        },
    }

    assert prepare_report_assets(
        context,
        ScanType.PASSIVE_CTEM,
    )


def test_active_reports_do_not_get_screenshot_access():
    assert not prepare_report_assets(
        {},
        ScanType.ACTIVE_VULNERABILITY,
    )