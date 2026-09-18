import os 
import psycopg2 
from psycopg2.extras import RealDictCursor 
import logging 
from typing import Any 
from contextlib import closing 
from urllib.parse import quote_plus 

logger = logging.getLogger(__name__)

def _get_db_url() -> str: 
    db_host = os.getenv("DATABASE_HOST")
    db_port = os.getenv("DATABASE_PORT", "5432") 
    db_name = os.getenv("DATABASE_NAME") 
    db_user = os.getenv("DATABASE_USER") 
    db_pass = os.getenv("DATABASE_PASSWORD") 

    if not all([db_host, db_name, db_user, db_pass]): 

        full_url = os.getenv("DATABASE_URL")
        if full_url: 
            return full_url.replace("+asyncpg", "")
        raise RuntimeError("Database configuration environment variables are missing.")

    return f"postgresql://{quote_plus(db_user)}:{quote_plus(db_pass)}@{db_host}:{db_port}/{db_name}"
