from app.services.report_storage_service import ReportStorageService

#can we save reports testin

def test_store_local(tmp_path):
    report = tmp_path / "report.pdf"
    report.write_text("test")
    result = (ReportStorageService.store_report
    (
        report,
        "scan-1",
    ))
    assert result == str(report)


def test_missing_report(tmp_path):
    report = tmp_path / "missing.pdf"
    try:
        (ReportStorageService.store_report
        (
            report,
            "scan-1",
        ))
        assert False
    except Exception:
        assert True