#type: ignore
from sqlalchemy.orm import Session

from app.models.user import User


def get_or_create_user(
    db: Session,
    auth_provider_id: str,
    email: str,
    full_name: str | None = None,
) -> User:
    user = (
        db.query(User)
        .filter(
            User.auth_provider == "keycloak",
            User.auth_provider_id == auth_provider_id,
        )
        .first()
    )

    if user:
        return user

    new_user = User(
        auth_provider="keycloak",
        auth_provider_id=auth_provider_id,
        email=email,
        full_name=full_name,
        role="client",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
