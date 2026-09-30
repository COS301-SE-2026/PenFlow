from unittest.mock import MagicMock
from app.tasks.schedule_tasks import dispatch_due_schedules_task


def test_schedule_happy(monkeypatch):
    loop = MagicMock()

    loop.run_until_complete.return_value =\
    {
        "status":"completed",
        "dispatched":2,
    }

    monkeypatch.setattr(
        "app.tasks.schedule_tasks.get_task_loop",
        lambda: loop,
    )

    result = dispatch_due_schedules_task.run()

    assert result["dispatched"] == 2