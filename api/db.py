"""DB connection for the FastAPI app. One connection per request — fine at demo scale."""

import os
import psycopg2
from urllib.parse import urlparse, unquote

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://recall_blast_radius_app:***REMOVED***@localhost:5432/recall_blast_radius",
)


def get_conn():
    p = urlparse(DATABASE_URL)
    return psycopg2.connect(
        host=p.hostname,
        port=p.port or 5432,
        dbname=p.path.lstrip("/"),
        user=p.username,
        password=unquote(p.password) if p.password else None,
    )
