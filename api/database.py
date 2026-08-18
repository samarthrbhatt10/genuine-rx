"""
Database connection dependency for FastAPI.
"""
import os
from typing import Generator
import psycopg
from psycopg.rows import dict_row

def get_db() -> Generator[psycopg.Connection, None, None]:
    """Dependency that provides a psycopg connection."""
    db_url = os.environ.get("GENUINE_RX_DB_URL", "postgresql://postgres:devpass@localhost:5433/genuine_rx")
    if not db_url:
        raise RuntimeError("GENUINE_RX_DB_URL is not set.")
        
    dsn = db_url.replace("postgresql+psycopg://", "postgresql://")
    
    conn = psycopg.connect(dsn, row_factory=dict_row, autocommit=True)
    try:
        yield conn
    finally:
        conn.close()
