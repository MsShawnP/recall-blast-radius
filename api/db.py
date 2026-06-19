"""DB connection for the FastAPI app. One connection per request — fine at demo scale."""

import os
import psycopg2
from urllib.parse import urlparse, unquote

def get_conn():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is required. "
            "Set it to your Postgres connection string (see .env.example)."
        )
    p = urlparse(database_url)
    return psycopg2.connect(
        host=p.hostname,
        port=p.port or 5432,
        dbname=p.path.lstrip("/"),
        user=p.username,
        password=unquote(p.password) if p.password else None,
    )
