from app.tasks.report_tasks import render_report_pdf_task

#success version
def test_report(monkeypatch):
    (monkeypatch.setattr
    (
        "app.tasks.report_tasks.generate_pdf_from_html",
        lambda **kwargs: "/tmp/report.pdf",
    ))
    (monkeypatch.setattr
    (
        "app.tasks.report_tasks.ReportStorageService.store_report",
        lambda **kwargs: "/tmp/report.pdf",
    ))
    (monkeypatch.setattr
    (
        "app.tasks.report_tasks.send_report_callback",
        lambda **kwargs: None,
    ))

    result = (render_report_pdf_task.run
    (
        "scan-1",
        "<html></html>",
        "/tmp/report.pdf",
    ))
    assert result["status"] == "completed"


#failed version
def test_report_failed(monkeypatch):
    (monkeypatch.setattr
    (
        "app.tasks.report_tasks.generate_pdf_from_html",
        lambda **kwargs: (_ for _ in ()).throw(Exception("failed")),
    ))
    (monkeypatch.setattr
    (
        "app.tasks.report_tasks.send_report_callback",
        lambda **kwargs: None,
    ))
    result = (render_report_pdf_task.run
    (
        "scan-1",
        "<html></html>",
        "/tmp/report.pdf",
    ))

    assert result["status"] == "failed"