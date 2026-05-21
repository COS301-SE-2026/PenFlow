#type: ignore
import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def get_or_create_user(
    db: Session,
    auth_provider_id: str,
    email: str,
    full_name: str | None = None,
) -> dict:
    result = db.execute(
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
    db.commit()
    row = result.fetchone()
    logger.info("[user_repo] provisioned user %s (%s)", row.id, row.email)
    return {"id": str(row.id), "email": row.email, "role": row.role}
