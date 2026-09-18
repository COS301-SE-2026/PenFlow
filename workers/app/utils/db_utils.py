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

def get_ports_from_db(scan_id: str) -> list[dict[str, Any]]:
    try:
        with closing(psycopg2.connect(_get_db_url())) as conn: 
            with conn.cursor(cursor_factory=RealDictCursor) as cursor: 
                cursor.execute(
                    "SELECT port, protocol, service_name as service, product, version, state "
                    "FROM services WHERE scan_id = %s",
                    (scan_id,)
                )
                return [dict(row) for row in cursor.fetchall()]
    except Exception as e: 
        logger.error(f"Failed to fetch ports from DB for scan {scan_id}: {e}")
        raise

def get_technologies_from_db(scan_id: str) -> list[dict[str, Any]]: 
    try: 
        with closing(psycopg2.connect(_get_db_url())) as conn: 
            with conn.cursor(cursor_factory=RealDictCursor) as cursor: 
                cursor.execute(
                    """
                    SELECT t.technology_type as category, t.product, t.version, 
                           t.confidence as evidence_score, s.host, s.port, s.protocol, 
                           t.evidence->>'cpe' as cpe 
                    FROM detected_technologies t 
                    LEFT JOIN services s ON t.service_id = s.id 
                    WHERE t.scan_id = %s
                    """,
                    (scan_id,)
                )
                rows = [] 
                for row in cursor.fetchall(): 
                    r = dict(row) 
                    r['host'] = r.get('host')
                    r['port'] = r.get('port') 
                    r['protocol'] = r.get('protocol')
                    rows.append(r)
                return rows 
    except Exception as e: 
        logger.error(f"Failed to fetch technologies from DB for scan {scan_id}: {e}")
        raise