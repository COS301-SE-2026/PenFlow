import os
from unittest.mock import MagicMock

os.environ["BACKEND_URL"] = "http://localhost:3001"
from app.utils.callback import (
    build_api_url,
    send_report_callback,
    send_scan_callback,
    send_source_callback,
)


#using our default api path
def test_build_url():
    result = build_api_url("/test")
    assert result == "http://localhost:3001/api/v1/test"

#scan
def test_scan_callback(monkeypatch):
    client = MagicMock()
    client.__enter__.return_value = client
    (monkeypatch.setattr
    (
        "app.utils.callback.httpx.Client",
        lambda **kwargs: client,
    ))
    send_scan_callback("scan-1", "completed")
    client.patch.assert_called_once()

#report
def test_report_callback(monkeypatch):
    client = MagicMock()
    client.__enter__.return_value = client
    (monkeypatch.setattr
    (
        "app.utils.callback.httpx.Client",
        lambda **kwargs: client,
    ))
    send_report_callback("scan-1", "completed")
    client.patch.assert_called_once()

#source
def test_source_callback(monkeypatch):
    client = MagicMock()
    client.__enter__.return_value = client
    (monkeypatch.setattr
    (
        "app.utils.callback.httpx.Client",
        lambda **kwargs: client,
    ))
    (send_source_callback
    (
        "scan-1",
        "hunter",
        "completed",
    ))
    client.patch.assert_called_once()