from unittest.mock import MagicMock

from app.tasks.rag_index_tasks import index_scan_task


def test_rag_happy(monkeypatch):
    loop = MagicMock()

    loop.run_until_complete.return_value = (
    {
        "total_findings":4,
        "indexed":3,
        "unchanged":1,
    })

    monkeypatch.setattr(
        "app.tasks.rag_index_tasks.get_task_loop",
        lambda: loop,
    )

    result = (index_scan_task.run
    (
        "1233-abcd-5678-efgh-sfewf3748"
    ))

    assert result["indexed"] == 3