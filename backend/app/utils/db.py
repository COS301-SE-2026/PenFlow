from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.conflict.database import SessionLocal 

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that yields an asynchronous database session for FastAPI routes.
    """
    async with SessionLocal() as db:
        yield db