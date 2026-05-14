from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.utils.db import get_db

router = APIRouter()

@router.get("/health")
def health_check() -> dict[str, str]:
    return {"backend": "ok"}

@router.get("/db-health")
def db_health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"database": "ok"}

