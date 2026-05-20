#type: ignore
import logging

from fastapi import APIRouter,Sepends, status
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
):

    """
    Infrastructure health check endpoint for Render/Docker.
    """
    db_status = "disconnected"

    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error("Database connection failed: %s", e)
    
    return {
        "status": "ok",
        "api_version": "1.0.0",
        "database": db_status
    }
