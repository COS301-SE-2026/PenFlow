from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi import status

@pytest.mark.asyncio
@patch("app.api.routes.summary.summary_repo.get_report_status", new_callable=AsyncMock)
@patch("app.api.routes.summary.summary_repo.get_source_coverage", new_callable=AsyncMock)
@patch("app.api.routes.summary.summary_repo.get_asset_impact_summary", new_callable=AsyncMock)
@patch("app.api.routes.summary.summary_repo.get_top_findings_preview", new_callable=AsyncMock)
@patch("app.api.routes.summary.summary_repo.get_risk_snapshot", new_callable=AsyncMock)
@patch("app.api.routes.summary.summary_repo.get_scan_summary", new_callable=AsyncMock)
async def test_get_scan_summary_success(
    mock_get_scan,
    mock_get_risk,
    mock_get_top_findings,
    mock_get_asset_impact,
    mock_get_source_coverage,
    mock_get_report,
    test_client
):
    scan_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    now = datetime.now(timezone.utc)

    # mocked scan object
    mock_scan_obj = MagicMock()
    mock_scan_obj.id = scan_id
    mock_scan_obj.domain = "test.co"
    mock_scan_obj.status = "completed"
    mock_scan_obj.progress = 100
    mock_scan_obj.created_at = now
    mock_scan_obj.started_at = now
    mock_scan_obj.completed_at = now
    mock_scan_obj.error_message = None
    mock_get_scan.return_value = mock_scan_obj

    # mocked risk snapshot
    mock_get_risk.return_value = {
        "total_findings": 10,
        "critical_count": 0,
        "high_count": 2,
        "medium_count": 3,
        "low_count": 5,
        "info_count": 0 
    }

    # mocked top findings
    mock_get_top_findings.return_value = [
        {
            "id": UUID("660e8400-e29b-41d4-a716-446655440000"),
            "severity": "high",
            "title": "Exposed credentials",
            "description": "Leaked email found.",
            "recommendation": "Change your password.",
            "source": "hibp",
            "asset_identifier": "admin@example.co",
            "asset_type": "email",
            "created_at": now
        }
    ]

    # mocked asset impact
    mock_get_asset_impact.return_value = {
        "total_assets_scanned": 5,
        "affectd_assets_count": 1,
        "asset_type_breakdown": [
            {"asset_type": "Email", "total_assets": 1, "affected_assets": 1}
        ],
        "top_affected_assets": [
            {
                "identifier": "admin@example.co",
                "asset_type": "email",
                "finding_count": 1,
                "highest_severity": "high"
            }
        ]
    }

    # mocked source coverage
    mock_get_source_coverage.return_value = {
        "aggregate": {
            "sources_total": 1,
            "sources_completed": 1,
            "sources_failed": 0,
            "sources_partial": 0,
            "sources_skipped": 0
        },
        "sources": [
            {
                "source_name": "hibp",
                "status": "completed",
                "started_at": now,
                "completed_at": now,
                "error_message": None
            }
        ]
    }

    # mocked report status
    mock_report_obj = MagicMock()
    mock_report_obj.status = "completed"
    mock_report_obj.generated_at = now
    mock_report_obj.pdf_path = "/reports/123.pdf"
    mock_report_obj.error_message = None
    mock_get_report.return_value = mock_report_obj

    #executing the request
    response = await test_client.get(f"/api/v1/scans/{scan_id}/summary")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["scan_summary"]["domain"] == "test.co"
    assert data["risk_snapshot"]["total_findings"] == 10
    assert len(data["top_findings"]) == 1
    assert data["asset_impact"]["total_assets_scanned"] == 5