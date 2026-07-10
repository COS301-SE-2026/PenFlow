import os
from pathlib import Path
from typing import cast

from dotenv import load_dotenv
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

ROOT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(ROOT_DIR / ".env")

def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        if database_url.startswith("postgres://"):
            return database_url.replace(
                "postgres://", 
                "postgresql+asyncpg://", 
                1,
            )
        
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace(
                "postgresql://", 
                "postgresql+asyncpg://", 
                1,
            )

        return database_url
    
    required_variables = (
        "DATABASE_HOST",
        "DATABASE_PORT",
        "DATABASE_NAME",
        "DATABASE_USER",
        "DATABASE_PASSWORD",
    )
 
    values = {
        variable: os.getenv(variable)
        for variable in required_variables
    }

    missing_vars = [
        variable
        for variable, value in values.items()
        if not value
    ]

    if missing_vars:
        raise RuntimeError(
            "Database config is missing. Missing: "
            + ", ".join(missing_vars)
        )
    
    database_host = cast(str, values["DATABASE_HOST"])
    database_port = cast(str, values["DATABASE_PORT"])
    database_name = cast(str, values["DATABASE_NAME"])
    database_user = cast(str, values["DATABASE_USER"])
    database_password = cast(str, values["DATABASE_PASSWORD"])

    return URL.create(
        drivername = "postgresql+asyncpg",
        username = database_user,
        password = database_password,
        host = database_host,
        port = int(database_port),
        database = database_name,
    ).render_as_string(hide_password=False)


DATABASE_URL = get_database_url()

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = async_sessionmaker(
    autocommit = False,
    autoflush = False,
    bind = engine,
)