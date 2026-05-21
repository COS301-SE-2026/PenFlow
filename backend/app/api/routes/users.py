#type: ignore
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.middleware.auth import get_current_user
from app.repositories.user_repo import get_or_create_user
from app.utils.db import get_db

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
def provision_user(
    current_user: dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = get_or_create_user(
        db=db,
        auth_provider_id=current_user["sub"],
        email=current_user.get("email", ""),
        full_name=current_user.get("name"),
    )

    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
    }
