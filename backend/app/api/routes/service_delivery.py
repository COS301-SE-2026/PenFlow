import os
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import require_service_delivery
from app.models.base import (
    AssessmentType,
    EngagementStatus,
    FindingStatus,
    Severity,
)
from app.models.user import User
from app.schemas.engagement import (
    ActivityListResponse,
    ServiceDeliveryConversationListResponse,
)
from app.schemas.retest import (
    RetestListItem,
    RetestListResponse,
)
from app.schemas.service_delivery import (
    ServiceDeliveryCancelRequest,
    ServiceDeliveryDashboardResponse,
    ServiceDeliveryEngagementActionResponse,
    ServiceDeliveryEngagementDetail,
    ServiceDeliveryEngagementListResponse,
    ServiceDeliveryFindingDetail,
    ServiceDeliveryFindingListResponse,
    ServiceDeliveryPentesterAssignment,
    ServiceDeliveryPentesterCreate,
    ServiceDeliveryPentesterDetail,
    ServiceDeliveryPentesterListResponse,
    ServiceDeliveryReassignRequest,
    ServiceDeliveryRescheduleRequest,
    ServiceDeliveryReviewReturnRequest,
    ServiceDeliveryScheduleRequest,
    ServiceDeliveryScopingUpdate,
)
from app.services.service_delivery_service import ServiceDeliveryService
from app.utils.db import get_db

router = APIRouter(
    prefix = "/service-delivery",
    tags=["Service Delivery"],
)

@router.get(
    "/engagements",
    response_model=ServiceDeliveryEngagementListResponse,
    summary="List engagements for Service Delivery",
)
async def list_service_delivery_engagements(
    engagement_status: Annotated[
        EngagementStatus | None,
        Query(alias="status"),
    ] = None,
    assessment_type: AssessmentType | None = None,
    search: Annotated[
        str | None,
        Query(max_length = 255),
    ] = None,
    pentester_id: UUID | None = None,
    assigned: bool | None = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0),
    ] = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> ServiceDeliveryEngagementListResponse:

    return await ServiceDeliveryService.list_engagements(
        db,
        engagement_status=engagement_status,
        assessment_type=assessment_type,
        search=search,
        pentester_id=pentester_id,
        assigned=assigned,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/engagements/{engagement_id}",
    response_model=ServiceDeliveryEngagementDetail,
    summary="Get Service Delivery engagement detail.",
)
async def get_service_delivery_engagement(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> ServiceDeliveryEngagementDetail:
    return await ServiceDeliveryService.get_engagement(
        db,
        engagement_id=engagement_id,
    )


@router.post(
    "/engagements/{engagement_id}/claim",
    response_model=ServiceDeliveryEngagementActionResponse,
    summary="Claim an engagement for scoping",
)
async def claim_service_delivery_engagement(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> ServiceDeliveryEngagementActionResponse:
    return await ServiceDeliveryService.claim_engagement(
        db,
        engagement_id=engagement_id,
        service_delivery_id=user.id,
    )


@router.patch(
    "/engagements/{engagement_id}/scoping",
    response_model=ServiceDeliveryEngagementActionResponse,
    summary="Update engagement scoping",
)
async def update_service_delivery_scoping(
    engagement_id: UUID,
    request: ServiceDeliveryScopingUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> ServiceDeliveryEngagementActionResponse:
    return await ServiceDeliveryService.update_scoping(
        db,
        engagement_id=engagement_id,
        service_delivery_id=user.id,
        request=request,
    )


@router.put(
    "/engagements/{engagement_id}/pentester",
    response_model=ServiceDeliveryEngagementActionResponse,
    summary="Assign pentester to engagement",
)
async def assign_service_delivery_pentester(
    engagement_id: UUID,
    request: ServiceDeliveryPentesterAssignment,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> ServiceDeliveryEngagementActionResponse:
    return await ServiceDeliveryService.assign_pentester(
        db,
        engagement_id=engagement_id,
        service_delivery_id=user.id,
        request=request,
    )


@router.post(
    "/engagements/{engagement_id}/schedule",
    response_model=ServiceDeliveryEngagementActionResponse,
    summary="Schedule an engagement",
)
async def schedule_service_delivery_engagement(
    engagement_id: UUID,
    request: ServiceDeliveryScheduleRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> ServiceDeliveryEngagementActionResponse:
    return await ServiceDeliveryService.schedule_engagement(
        db,
        engagement_id=engagement_id,
        service_delivery_id=user.id,
        request=request,
    )


@router.post(
    "/engagements/{engagement_id}/reassign",
    response_model=ServiceDeliveryEngagementActionResponse,
    summary="Reassign scheduled engagement",
)
async def reassign_service_delivery_pentester(
    engagement_id: UUID,
    request: ServiceDeliveryReassignRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> ServiceDeliveryEngagementActionResponse:
    return await ServiceDeliveryService.reassign_pentester(
        db,
        engagement_id=engagement_id,
        service_delivery_id=user.id,
        request=request,
    )


@router.post(
    "/engagements/{engagement_id}/reschedule",
    response_model=ServiceDeliveryEngagementActionResponse,
    summary="Reschedule an engagement",
)
async def reschedule_service_delivery_engagement(
    engagement_id: UUID,
    request: ServiceDeliveryRescheduleRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> ServiceDeliveryEngagementActionResponse:
    return await ServiceDeliveryService.reschedule_engagement(
        db,
        engagement_id=engagement_id,
        service_delivery_id=user.id,
        request=request,
    )


@router.post(
    "/engagements/{engagement_id}/review/return",
    response_model=ServiceDeliveryEngagementActionResponse,
    summary="Return engagement to pentester",
)
async def return_service_delivery_review(
    engagement_id: UUID,
    request: ServiceDeliveryReviewReturnRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> ServiceDeliveryEngagementActionResponse:
    return await ServiceDeliveryService.return_from_review(
        db,
        engagement_id=engagement_id,
        service_delivery_id=user.id,
        request=request,
    )


@router.post(
    "/engagements/{engagement_id}/review/complete",
    response_model=ServiceDeliveryEngagementActionResponse,
    summary="Complete engagement review",
)
async def complete_service_delivery_review(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> ServiceDeliveryEngagementActionResponse:
    return await ServiceDeliveryService.complete_review(
        db,
        engagement_id=engagement_id,
        service_delivery_id=user.id,
    )


@router.post(
    "/engagements/{engagement_id}/cancel",
    response_model=ServiceDeliveryEngagementActionResponse,
    summary="Cancel an engagement",
)
async def cancel_service_delivery_engagement(
    engagement_id: UUID,
    request: ServiceDeliveryCancelRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> ServiceDeliveryEngagementActionResponse:
    return await ServiceDeliveryService.cancel_engagement(
        db,
        engagement_id=engagement_id,
        service_delivery_id=user.id,
        request=request,
    )


@router.get(
    "/dashboard",
    response_model=ServiceDeliveryDashboardResponse,
    summary="Get Service Delivery dashboard",
)
async def get_service_delivery_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> ServiceDeliveryDashboardResponse:
    return await ServiceDeliveryService.get_dashboard(db)


@router.get(
    "/pentesters",
    response_model=ServiceDeliveryPentesterListResponse,
    summary="List pentesters",
)
async def list_service_delivery_pentesters(
    search: Annotated[
        str | None,
        Query(max_length=255),
    ] = None,
    assessment_type: AssessmentType | None = None,
    availability_status: str | None = None,
    is_active: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> ServiceDeliveryPentesterListResponse:
    return await ServiceDeliveryService.list_pentesters(
        db,
        search=search,
        assessment_type=assessment_type,
        availability_status=availability_status,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )

@router.get(
    "/pentesters/{pentester_id}",
    response_model=ServiceDeliveryPentesterDetail,
    summary="Get pentester detail",
)
async def get_service_delivery_pentester(
    pentester_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> ServiceDeliveryPentesterDetail:
    return await ServiceDeliveryService.get_pentester(
        db,
        pentester_id=pentester_id,
    )


@router.post(
    "/pentesters",
    response_model=ServiceDeliveryPentesterDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create pentester",
)
async def create_service_delivery_pentester(
    request: ServiceDeliveryPentesterCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> ServiceDeliveryPentesterDetail:
    return await ServiceDeliveryService.create_pentester(
        db,
        service_delivery_user_id=user.id,
        request=request,
    )


@router.delete(
        "/pentesters/{pentester_id}",
        response_model=ServiceDeliveryPentesterDetail,
        status_code=status.HTTP_200_OK,
        summary="Deactivate a pentester",
)
async def deactivate_service_delivery_pentester(
    pentester_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> ServiceDeliveryPentesterDetail:
    return await ServiceDeliveryService.deactivate_pentester(
        db,
        service_delivery_user_id=user.id,
        pentester_id=pentester_id,
    )

@router.get(
    "/engagements/{engagement_id}/findings",
    response_model=ServiceDeliveryFindingListResponse,
    summary="List engagement findings",
)
async def list_service_delivery_findings(
    engagement_id: UUID,
    severity: Severity | None = None,
    finding_status: Annotated[
        FindingStatus | None,
        Query(alias="status"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> ServiceDeliveryFindingListResponse:
    return await ServiceDeliveryService.list_findings(
        db,
        engagement_id=engagement_id,
        service_delivery_id=user.id,
        severity=severity,
        finding_status=finding_status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/engagements/{engagement_id}/findings/{finding_id}",
    response_model=ServiceDeliveryFindingDetail,
    summary="Get engagement finding",
)
async def get_service_delivery_finding(
    engagement_id: UUID,
    finding_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> ServiceDeliveryFindingDetail:
    return await ServiceDeliveryService.get_finding(
        db,
        engagement_id=engagement_id,
        finding_id=finding_id,
        service_delivery_id=user.id,
    )


@router.get(
    "/evidence/{evidence_id}/download",
    response_class=FileResponse,
    summary="Download finding evidence",
)
async def download_service_delivery_evidence(
    evidence_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> FileResponse:
    evidence = await ServiceDeliveryService.get_evidence_for_download(
        db,
        evidence_id=evidence_id,
        service_delivery_id=user.id,
    )

    storage_root = Path(
        os.getenv(
            "EVIDENCE_STORAGE_DIR",
            "/tmp/penflow-evidence",
        )
    ).resolve()

    file_path = Path(evidence.file_path).resolve()

    if not file_path.is_relative_to(storage_root):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence file not found.",
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence file is no longer available.",
        )

    return FileResponse(
        path=file_path,
        filename=evidence.file_name,
        media_type=evidence.mime_type or "application/octet-stream",
        headers={
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get(
    "/engagements/{engagement_id}/retests",
    response_model=RetestListResponse,
    summary="List retests for an engagement",
)
async def get_service_delivery_engagement_retests(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> RetestListResponse:
    return await ServiceDeliveryService.list_retests(
        db,
        engagement_id=engagement_id,
        service_delivery_id=user.id,
    )


@router.get(
    "/retests/{retest_id}",
    response_model=RetestListItem,
    summary="Get retest details",
)
async def get_service_delivery_retest(
    retest_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> RetestListItem:
    return await ServiceDeliveryService.get_retest(
        db,
        retest_id=retest_id,
        service_delivery_id=user.id,
    )


@router.get(
    "/messages",
    response_model=ServiceDeliveryConversationListResponse,
    summary="Get service delivery messages",
)
async def get_service_delivery_messages (
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> ServiceDeliveryConversationListResponse:
    return await ServiceDeliveryService.get_message_conversations(
        db,
        service_delivery_id=user.id,
    )


@router.get(
    "/audit",
    response_model=ActivityListResponse,
    summary="List service delivery audit activity",
)
async def get_service_delivery_audit(
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_service_delivery),
) -> ActivityListResponse:
    return await ServiceDeliveryService.list_audit(
        db,
        service_delivery_id=user.id,
        limit=limit,
        offset=offset,
    )