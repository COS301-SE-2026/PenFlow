#type: ignore
import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def get_or_create_user(
    db: AsyncSession,
    auth_provider_id: str,
    email: str,
    full_name: str | None = None,
) -> dict:
    result = await db.execute(
        text("""
            INSERT INTO users (auth_provider, auth_provider_id, email, full_name, role)
            VALUES ('keycloak', :auth_provider_id, :email, :full_name, 'client')
            ON CONFLICT (auth_provider, auth_provider_id) DO UPDATE
                SET email      = EXCLUDED.email,
                    full_name  = EXCLUDED.full_name
            RETURNING id, email, role
        """),
        {
            "auth_provider_id": auth_provider_id,
            "email": email,
            "full_name": full_name,
        },
    )
    await db.commit()
    row = result.fetchone()
    logger.info("[user_repo] provisioned user %s (%s)", row.id, row.email)
    return {"id": str(row.id), "email": row.email, "role": row.role}


async def get_user_id_by_provider_id(
    db: AsyncSession,
    auth_provider_id: str,
) -> UUID | None:
    result = await db.execute(
        text("SELECT id FROM users WHERE auth_provider_id = :auth_provider_id"),
        {"auth_provider_id": auth_provider_id},
    )
    row = result.fetchone()
    return row.id if row else None