from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_user
from app.repositories.user_repo import get_user_id_by_provider_id
from app.schemas.scan_schedule import ScanScheduleCreate, ScanScheduleResponse, ScanScheduleUpdate
from app.services.scan_schedule_service import ScanScheduleService
from app.utils.db import get_db

router = APIRouter(
    prefix="/scan-schedules",
    tags=["Scan Schedules"],
)

db_session = Annotated[AsyncSession, Depends(get_db)]
current_user = Annotated[dict[str, Any], Depends(get_current_user)]

async def resolve_user_id(
    db: AsyncSession,
    current_user: dict[str, Any],
) -> UUID:
    user_id = await get_user_id_by_provider_id(
        db,
        current_user["sub"],
    )

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not present.",
        )

    return user_id


@router.post(
    "",
    response_model=ScanScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule(
    request: ScanScheduleCreate,
    db: db_session,
    current_user: current_user,
) -> ScanScheduleResponse:
    user_id = await resolve_user_id(
        db,
        current_user,
    )

    schedule = await ScanScheduleService.create_schedule(
        db,
        user_id=user_id,
        request=request,
    )

    return ScanScheduleResponse.model_validate(schedule)


@router.get(
    "",
    response_model=list[ScanScheduleResponse],
)
async def list_schedules(
    db: db_session,
    current_user: current_user,
) -> list[ScanScheduleResponse]:
    user_id = await resolve_user_id(
        db,
        current_user,
    )

    schedules = await ScanScheduleService.list_schedules(
        db,
        user_id=user_id,
    )

    return [
        ScanScheduleResponse.model_validate(schedule)
        for schedule in schedules
    ]


@router.get(
    "/{schedule_id}",
    response_model=ScanScheduleResponse,
)
async def get_schedule(
    schedule_id: UUID,
    db: db_session,
    current_user: current_user,
) -> ScanScheduleResponse:
    user_id = await resolve_user_id(
        db,
        current_user,
    )

    schedule = await ScanScheduleService.get_schedule(
        db,
        schedule_id=schedule_id,
        user_id=user_id,
    )

    return ScanScheduleResponse.model_validate(schedule)


@router.patch(
    "/{schedule_id}",
    response_model=ScanScheduleResponse,
) 
async def update_schedule(
    schedule_id: UUID,
    request: ScanScheduleUpdate,
    db: db_session,
    current_user: current_user,
) -> ScanScheduleResponse:
    user_id = await resolve_user_id(
        db,
        current_user,
    )

    schedule = await ScanScheduleService.update_schedule(
        db,
        schedule_id=schedule_id,
        user_id=user_id,
        request=request,
    )

    return ScanScheduleResponse.model_validate(schedule)


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
) 
async def delete_schedule(
    schedule_id: UUID,
    db: db_session,
    current_user: current_user,
) -> Response:
    user_id = await resolve_user_id(
        db,
        current_user,
    )

    await ScanScheduleService.delete_schedule(
        db,
        schedule_id=schedule_id,
        user_id=user_id,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)