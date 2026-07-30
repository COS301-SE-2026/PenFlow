#route contract test for scans endpoints : hit the real fastapi via test_client
# mock scan repo itself but not the request pipeline

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi import status

from app.api.middleware.auth import get_current_user_optional
from app.main import app
from app.models.user import User
from app.models.verified_domain import DomainVerificationStatus, VerifiedDomain
from app.repositories.scan_repo import ScanRepository


#phase2
#test initate scan success 
@pytest.mark.asyncio
@patch("app.services.scan_service.celery_app.send_task")
async def test_initiate_scan_success(mock_send_task, test_client, db_session):
    mock_send_task.return_value = MagicMock(id="mock-task-id")

    payload = {
        "domain": "real-db-scan.com",
        "email": "jeandre@gmail.com",
    }

    response = await test_client.post("/api/v1/scans/", json=payload)

    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()
    assert data["status"] == "queued"

    scan = await ScanRepository.get_scan_by_id(db_session, UUID(data["scan_id"]))
    assert scan is not None
    assert scan.domain == "real-db-scan.com"
    assert scan.email == "jeandre@gmail.com"

    mock_send_task.assert_called_once()
    args, _ = mock_send_task.call_args
    assert args[0] == "scan.full"


@pytest.mark.asyncio
async def test_initiate_scan_invalid_domain(test_client):
    """Test missing required fields give a 422 Validation error"""
    payload = {
        #In this case I'll remove domain
        "email": "Jeandre@gmail.com"
    }
    response = await test_client.post("/api/v1/scans/",json=payload)
    #Where pydantic comes in
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

@pytest.mark.asyncio
@patch("app.api.routes.scans.get_report_by_scan_id")
async def test_download_scan_pdf(mock_get_report, test_client, tmp_path):
    """Test that the pdf endpoint returns a file with correct headers"""
    test_pdf = tmp_path / "test.pdf"
    test_pdf.write_bytes(b"%PDF-1.4\n%test pdf\n")
    mock_report = MagicMock()
    mock_report.status.value = "completed"
    mock_report.pdf_path = str(test_pdf)

    mock_get_report.return_value = mock_report

    response = await test_client.get(
        "/api/v1/scans/550e8400-e29b-41d4-a716-446655440000/pdf"
    )

    assert response.status_code == status.HTTP_200_OK

@pytest.mark.asyncio
@patch("app.api.routes.internal.ScanRepository.get_scan_by_id", new_callable=AsyncMock)
async def test_worker_failure_callback(mock_get_scan_by_id, test_client):
    mock_scan_id = "550e8400-e29b-41d4-a716-446655440000"

    mock_scan = MagicMock()
    mock_scan.id = UUID(mock_scan_id)
    mock_scan.status.value = "failed"
    mock_get_scan_by_id.return_value = mock_scan

    payload = {
        "status": "failed",
        "error_message": "Shodan API rate limit exceeded",
    }

    response = await test_client.patch(
        f"/api/v1/internal/scans/{mock_scan_id}/status",
        json=payload,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "failed"



@pytest.mark.asyncio
@patch("app.api.routes.scans.ScanRepository.get_scan_status", new_callable=AsyncMock)
async def test_get_scan_status_success(mock_get_status, test_client):
    mock_get_status.return_value = {
        "scan_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "running",
        "progress": 60,
        "sources": [],
        "report_status": None
    }

    response = await test_client.get("/api/v1/scans/550e8400-e29b-41d4-a716-446655440000/status")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["progress"] == 60

@pytest.mark.asyncio
@patch("app.api.routes.scans.ScanRepository.get_scan_status", new_callable=AsyncMock)
async def test_get_scan_status_not_found(mock_get_status, test_client):
    mock_get_status.return_value = None

    response = await test_client.get("/api/v1/scans/550e8400-e29b-41d4-a716-446655440000/status")

    assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
@patch("app.api.routes.scans.send_report_email")
@patch("app.api.routes.scans.get_report_by_scan_id", new_callable=AsyncMock)
@patch("app.api.routes.scans.ScanRepository.get_scan_by_id", new_callable=AsyncMock)
async def test_email_scan_report_success(
    mock_get_scan, 
    mock_get_report, 
    mock_send_email, 
    test_client
    ):
    # mocking the scan
    mock_scan =  MagicMock()
    mock_scan.domain = "jeandre.co"
    mock_get_scan.return_value = mock_scan

    # mock the compiled report
    mock_report = MagicMock()
    mock_report.status.value = "completed"
    mock_report.pdf_path = "/tmp/report.pdf"
    mock_get_report.return_value = mock_report

    payload = {"email": "client@example.co"}

    response = await test_client.post(
        "/api/v1/scans/550e8400-e29b-41d4-a716-446655440000/email-report",
        json=payload
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Report emailed successfully"
    mock_send_email.assert_called_once_with(
        to_email="client@example.co",
        domain="jeandre.co",
        pdf_path="/tmp/report.pdf"
    )

@pytest.mark.asyncio
@patch("app.api.routes.scans.get_report_by_scan_id")
async def test_download_scan_pdf_report_missing(mock_get_report, test_client):
    mock_get_report.return_value = None

    response = await test_client.get(
        "/api/v1/scans/550e8400-e29b-41d4-a716-446655440000/pdf",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
@patch("app.api.routes.scans.get_report_by_scan_id")
async def test_download_scan_pdf_uncompleted(mock_get_report, test_client):
    mock_report = MagicMock()
    mock_report.status.value = "generating"
    mock_get_report.return_value = mock_report
    response = await test_client.get(
        "/api/v1/scans/550e8400-e29b-41d4-a716-446655440000/pdf"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST

#Test success scan :list_scan tests (Get/scans)
@pytest.mark.asyncio
@patch("app.api.routes.scans.ScanRepository.list_scans",new_callable =AsyncMock)
@patch("app.api.routes.scans.get_user_id_by_provider_id",new_callable =AsyncMock)
async def test_list_scans_success_authenticated(mock_get_user_id,mock_list_scans,test_client,
login_as):

    login_as ({"sub":"kc-123","email":"user@example.com"})
    mock_get_user_id.return_value = UUID("550e8400-e29b-41d4-a716-446655440000")
    mock_list_scans.return_value =[]

    response =await test_client.get("/api/v1/scans/")

    assert response.status_code ==status.HTTP_200_OK
    assert response.json() == []

#Test User not found
@pytest.mark.asyncio
@patch("app.api.routes.scans.get_user_id_by_provider_id",new_callable=AsyncMock)
async def test_list_scan_user_not_found(mock_get_user_id,test_client,login_as):
      login_as({"sub": "kc-unknown", "email": "ghost@example.com"})
      mock_get_user_id.return_value = None
       
      response = await test_client.get("/api/v1/scans/")

      assert response.status_code ==status.HTTP_404_NOT_FOUND
 
#Test Internal Error
@pytest.mark.asyncio
@patch("app.api.routes.scans.ScanRepository.list_scans",new_callable =AsyncMock)
@patch("app.api.routes.scans.get_user_id_by_provider_id",new_callable =AsyncMock)
async def test_list_scans_internal_error(mock_get_user_id, mock_list_scans,
test_client, login_as):
    login_as({"sub": "kc-123", "email": "user@example.com"})
    mock_get_user_id.return_value =UUID("550e8400-e29b-41d4-a716-446655440000")
    mock_list_scans.side_effect = RuntimeError("db exploded")

    response = await test_client.get("/api/v1/scans/")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


#Authenticated User Attaches User ID ,initiate scan with Auth (POST/scans)
@pytest.mark.asyncio
@patch("app.services.scan_service.celery_app.send_task")
@patch("app.repositories.scan_repo.ScanRepository.create_scan",new_callable=AsyncMock)
@patch("app.api.routes.scans.get_user_id_by_provider_id",new_callable =AsyncMock)
async def test_initiate_scan_authenticated_user_attaches_user_id(
    mock_get_user_id,mock_create_scan,mock_send_task,test_client
):

    app.dependency_overrides[get_current_user_optional] =  lambda: {
        "sub": "kc-123",
        "email": "user@example.com",
    }

    try:
        mock_get_user_id.return_value = UUID("550e8400-e29b-41d4-a716-446655440000")

        mock_scan = MagicMock()
        mock_scan.id = UUID("660e8400-e29b-41d4-a716-446655440000")
        mock_scan.status = "queued"
        mock_create_scan.return_value = mock_scan
        mock_send_task.return_value = MagicMock(id="mock-task-id")



        response = await test_client.post (
            "/api/v1/scans/",
        json={"domain": "Jeandre.co", "email": "jeandre@gmail.com"},
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        mock_create_scan.assert_awaited_once()
        _, kwargs = mock_create_scan.call_args
        assert kwargs["user_id"] == UUID("550e8400-e29b-41d4-a716-446655440000")
    finally:
        app.dependency_overrides.pop(get_current_user_optional,None)

#test: scan status not found 200 
@pytest.mark.asyncio 
@patch("app.api.routes.scans.ScanRepository.get_scan_status",new_callable =AsyncMock)
async def test_get_scan_status_found(mock_get_status,test_client):
    mock_get_status.return_value = {
        "scan_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "running",
        "progress": 42,
        "source": [] ,
        "report_status" : None, 
    }

    response = await test_client.get(
        "/api/v1/scans/550e8400-e29b-41d4-a716-446655440000/status"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["progress"] == 42


#phase2
#POST /scans/ (scan_type=active_vulnerability) happy path intergration
# celery_app.send_task is mocked 
# else hits the real test db via db_session/test_client
@pytest.mark.asyncio
@patch("app.services.scan_service.celery_app.send_task")
async def test_initiate_active_scan_success(mock_send_task, test_client, db_session):  
    
    mock_send_task.return_value = MagicMock(id="mock-task-id")

    user = User(
        auth_provider="keycloak",
        auth_provider_id="active-scan-user",
        email="activescan@example.com",
        full_name="Active Scan User",
        role="client",
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)

    verified_domain = VerifiedDomain(
        user_id=user.id,
        domain="verified-active.com",
        status=DomainVerificationStatus.VERIFIED,
        verification_token="penflow-verification=abc123",
    )
    db_session.add(verified_domain)
    await db_session.flush()
    await db_session.refresh(verified_domain)

    # Add dependency override
    app.dependency_overrides[get_current_user_optional] = lambda: {
        "sub": "active-scan-user",
        "email": "activescan@example.com",
    }
    try:
        payload = {
            "domain": "verified-active.com",
            "scan_type": "active_vulnerability",
            "verified_domain_id": str(verified_domain.id),
        }
        response =await test_client.post("/api/v1/scans/", json=payload)
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["status"] == "queued"
        mock_send_task.assert_called_once()
        args, _ = mock_send_task.call_args
        assert args[0] == "scan.phase2_full"
    finally:
        app.dependency_overrides.pop(get_current_user_optional, None)
