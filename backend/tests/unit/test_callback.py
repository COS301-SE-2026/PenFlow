from unittest.mock import MagicMock
from app.utils.callback import (
    send_engagement_report_callback,
    send_report_callback,
    send_scan_callback,
    send_source_callback,
)


def test_scan_happy(monkeypatch):
    response = MagicMock()
    response.json.return_value = {"status":"done"}

    monkeypatch.setattr(
        "app.utils.callback.httpx.patch",
        lambda *args,**kwargs: response,
    )

    result = send_scan_callback("jerry","completed")

    assert result["status"] == "done"


def test_scan_sad(monkeypatch):
    monkeypatch.setattr(
        "app.utils.callback.httpx.patch",
        lambda *args,**kwargs: (_ for _ in ()).throw(Exception("nope")),
    )

    result = send_scan_callback("bob","failed")

    assert result is None


def test_source_happy(monkeypatch):
    response = MagicMock()
    response.json.return_value = {"status":"done"}

    monkeypatch.setattr(
        "app.utils.callback.httpx.patch",
        lambda *args,**kwargs: response,
    )

    result = (send_source_callback
    (
        "tim",
        "hunter",
        {"status":"completed"},
    ))

    assert result["status"] == "done"


def test_report_happy(monkeypatch):
    response = MagicMock()
    response.json.return_value = {"status":"done"}

    monkeypatch.setattr(
        "app.utils.callback.httpx.patch",
        lambda *args,**kwargs: response,
    )

    result = send_report_callback("steve","completed")

    assert result["status"] == "done"


def test_engagement_happy(monkeypatch):
    response = MagicMock()
    response.json.return_value = {"status":"done"}

    monkeypatch.setattr(
        "app.utils.callback.httpx.put",
        lambda *args,**kwargs: response,
    )

    result = (send_engagement_report_callback
    (
        "dave",
        1,
        "completed",
    ))

    assert result["status"] == "done"