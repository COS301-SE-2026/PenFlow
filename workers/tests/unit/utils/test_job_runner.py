from app.utils.job_runner import dispatch_scan_job


def test_local_job(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "local")
    (monkeypatch.setattr
    (
        "app.utils.job_runner._run_local_docker_container",
        lambda command, env_vars: True,
    ))
    result = (dispatch_scan_job
    (
        "hunter",
        {"scan_id": "scan-1"},
    ))
    assert result is True


def test_production_job(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    (monkeypatch.setattr
    (
        "app.utils.job_runner._run_fargate_task",
        lambda command: True,
    ))
    result = (dispatch_scan_job
    (
        "hunter",
        {"scan_id": "scan-1"},
    ))
    assert result is True