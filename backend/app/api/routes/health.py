import logging
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.db import get_db

router = APIRouter(tags=["System"])
logger = logging.getLogger(__name__)

@router.get(
    "/health",
    status_code=status.HTTP_200_OK

)

async def health_check(
    db: AsyncSession = Depends(get_db)
)-> Any:

    """
    Infrastructure health check endpoint for Render/Docker.
    """
    db_status = "disconnected"

    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        logger.exception("Database connection failed")
    
    return {
        "status": "ok",
        "api_version": "1.0.0",
        "database": db_status
    }
