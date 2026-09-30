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
    (monkeypatch.setattr
    (
        "app.tasks.full_scan_tasks.celery_app.send_task",
        lambda task, args: tasks.append(task),
    ))
    result = run_phase2_full_scan.run("scan-1", "huterone.com")
    assert result["status"] == "queued"
    assert len(tasks) == 4