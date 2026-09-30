import os
from unittest.mock import MagicMock
os.environ["INTERNAL_WEBHOOK_SECRET"] = "test-secret"
from app.tasks.brand_monitoring_tasks import run_brand_monitoring_task


def test_brand_monitoring(monkeypatch):
    (monkeypatch.setattr
    (
        "app.tasks.brand_monitoring_tasks.TyposquatService.generate_candidates",
        lambda domain:
        [
            {
                "candidate_domain": "hacker0ne.com",
                "normalized_domain": "hacker0ne.com",
                "mutation_type": "homoglyph",
                "mutation_detail": "changed l to 1",
            }
        ],
    ))

    monkeypatch.setattr(
        "app.tasks.brand_monitoring_tasks.BrandSignalService.gather_signals",
        lambda domain: {
            "is_resolvable": True,
        },
    )

    monkeypatch.setattr(
        "app.tasks.brand_monitoring_tasks.BrandScoringService.evaluate",
        lambda candidate, signals: (
            80,
            "high",
            {"reasons": ["test"]},
        ),
    )

    response = MagicMock()
    response.raise_for_status.return_value = None

    monkeypatch.setattr(
        "app.tasks.brand_monitoring_tasks.requests.post",
        lambda *args, **kwargs: response,
    )

    result = run_brand_monitoring_task.run(
        "monitor-1",
        "hackerone.com",
    )

    assert result["status"] == "completed"
    assert result["brand_monitoring_id"] == "monitor-1"
    assert result["candidates_found"] == 1


def test_no_candidates(monkeypatch):
    monkeypatch.setattr(
        "app.tasks.brand_monitoring_tasks.TyposquatService.generate_candidates",
        lambda domain: [],
    )

    response = MagicMock()
    response.raise_for_status.return_value = None

    monkeypatch.setattr(
        "app.tasks.brand_monitoring_tasks.requests.post",
        lambda *args, **kwargs: response,
    )

    result = run_brand_monitoring_task.run(
        "monitor-1",
        "hackerone.com",
    )

    assert result["status"] == "completed"
    assert result["candidates_found"] == 0