from app.tasks.hunter_tasks import run_hunter


def test_hunter(monkeypatch):
    (monkeypatch.setattr
    (
        "app.tasks.hunter_tasks.send_source_callback",
        lambda **kwargs: None,
    ))

    (monkeypatch.setattr
    (
        "app.tasks.hunter_tasks.collect_raw_data",
        lambda domain: {"data": {}},
    ))

    (monkeypatch.setattr
    (
        "app.tasks.hunter_tasks.normalize_data",
        lambda data: {"phishing_surface": {}},
    ))

    (monkeypatch.setattr
    (
        "app.tasks.hunter_tasks.generate_findings_and_assets",
        lambda data: ([], []),
    ))

    result = run_hunter.run("scan-1", "hunter.com")
    assert result["status"] == "completed"
    assert result["source_name"] == "hunter.io"



def test_hunter_failed(monkeypatch):
    (monkeypatch.setattr
    (
        "app.tasks.hunter_tasks.send_source_callback",
        lambda **kwargs: None,
    ))

    (monkeypatch.setattr
    (
        "app.tasks.hunter_tasks.collect_raw_data",
        lambda domain: (_ for _ in ()).throw(Exception("failed")),
    ))

    result = run_hunter.run("scan-1", "hunter.com")
    assert result["status"] == "failed"