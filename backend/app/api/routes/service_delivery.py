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

@router.post(
    "/engagements/{engagement_id}/claim",
    response_model=ServiceDeliveryEngagementActionResponse,
    summary="Claim an engagement for scoping",
)

@router.patch(
    "/engagements/{engagement_id}/scoping",
    response_model=ServiceDeliveryEngagementActionResponse,
    summary="Update engagement scoping",
)

@router.put(
    "/engagements/{engagement_id}/pentester",
    response_model=ServiceDeliveryEngagementActionResponse,
    summary="Assign pentester to engagement",
)

@router.post(
    "/engagements/{engagement_id}/schedule",
    response_model=ServiceDeliveryEngagementActionResponse,
    summary="Schedule an engagement",
)

@router.post(
    "/engagements/{engagement_id}/reassign",
    response_model=ServiceDeliveryEngagementActionResponse,
    summary="Reassign scheduled engagement",
)

@router.post(
    "/engagements/{engagement_id}/reschedule",
    response_model=ServiceDeliveryEngagementActionResponse,
    summary="Reschedule an engagement",
)

@router.post(
    "/engagements/{engagement_id}/review/return",
    response_model=ServiceDeliveryEngagementActionResponse,
    summary="Return engagement to pentester",
)

@router.post(
    "/engagements/{engagement_id}/review/complete",
    response_model=ServiceDeliveryEngagementActionResponse,
    summary="Complete enagagement review",
)

@router.post(
    "/engagements/{engagement_id}/cancel",
    response_model=ServiceDeliveryEngagementActionResponse,
    summary="Cancel an engagement",
)

@router.get(
    "/dashboard",
    response_model=ServiceDeliveryDashboardResponse,
    summary="Get Service Delivery dashboard",
)

@router.get(
    "/pentesters",
    response_model=ServiceDeliveryPentesterListResponse,
    summary="List pentesters",
)

@router.get(
    "/pentesters/{pentester_id}",
    response_model=ServiceDeliveryPentesterDetail,
    summary="Get pentester detail",
)

#@router.post(
#    "/pentesters",
#    response_model=ServiceDeliveryPentesterDetail,
#    status_code=status.HTTP_201_CREATED,
#    summary="Create pentester",
#)

@router.get(
    "/engagements/{engagement_id}/findings",
    response_model=ServiceDeliveryFindingListResponse,
    summary="List engagement findings",
)

@router.get(
    "/engagements/{engagement_id}/findings/{finding_id}",
    response_model=ServiceDeliveryDashboardResponse,
    summary="Get engagement finding",
)

@router.get(
    "/evidence/{evidence_id}/download",
    response_class=FileResponse,
    summary="Download finding evidence",
)

@router.get(
    "/engagements/{engagement_id}/retests",
    response_model=RetestListResponse,
    summary="List retests for an engagement",
)

@router.get(
    "/retests/{retest_id}",
    response_model=RetestListItem,
    summary="Get retest details",
)

@router.get(
    "/messages",
    response_model=ServiceDeliveryConversationListResponse,
    summary="Get service delivery messages",
)

@router.get(
    "/audit",
    response_model=ActivityListResponse,
    summary="List service delivery audit activity",
)