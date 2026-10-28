from unittest.mock import Mock

from app.tasks.full_scan_tasks import run_full_scan, run_phase2_full_scan


#can we initiate a scan
def test_full_scan(monkeypatch):
    tasks = []
    (monkeypatch.setattr
    (
        "app.tasks.full_scan_tasks.celery_app.send_task",
        lambda task, args: tasks.append(task),
    ))
    result = run_full_scan.run("scan-1", "hunterone.com")
    assert result["status"] == "queued"
    assert len(tasks) == 6

#phase2
def test_phase2_scan(monkeypatch):
    tasks = []
    domain = "huterone.com"

    authorise = Mock(return_value={"domain": domain})
    callback = Mock()

    monkeypatch.setattr(
        "app.tasks.full_scan_tasks.require_phase2_authorisation",
        authorise,
    )
    monkeypatch.setattr(
        "app.tasks.full_scan_tasks.send_scan_callback",
        callback,
    )
    monkeypatch.setattr(
        "app.tasks.full_scan_tasks.celery_app.send_task",
        lambda task, args: tasks.append((task, args)),
    )

    result = run_phase2_full_scan.run("scan-1", domain)

    authorise.assert_called_once_with(
        "scan-1",
        stage="bootstrap",
        domain=domain,
    )
    callback.assert_not_called()

    assert result["status"] == "queued"
    assert tasks == [
        ("scan.dns", ["scan-1", domain]),
        ("scan.shodan", ["scan-1", domain]),
        ("scan.hibp", ["scan-1", domain]),
        ("scan.crt_sh", ["scan-1", domain, True]),
    ]