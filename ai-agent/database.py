"""
Database connection layer.
We use SQLAlchemy Core with raw parameterized SQL.

The engine is created LAZILY on first use so the backend starts up
instantly even when the remote MySQL is unreachable from localhost.
"""
import logging
from sqlalchemy import create_engine, text
from config import DATABASE_URL

logger = logging.getLogger("billerq-db")

_engine = None  # created on first call to run_query()

def _get_engine():
    global _engine
    if _engine is None:
        logger.info("Initializing database engine (lazy)...")
        _engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=False,         # don't ping on checkout — we'll catch errors in run_query
            pool_recycle=3600,
            connect_args={"connect_timeout": 5}  # 5-second timeout per connection attempt
        )
    return _engine

def run_query(sql: str, params: dict) -> list[dict]:
    """
    Run a parameterized SELECT query and return rows as a list of dicts.
    Raises RuntimeError if the DB is unreachable (caller should fallback to REST agent).
    """
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            result = conn.execute(text(sql), params)
            rows = [dict(row._mapping) for row in result]
        return rows
    except Exception as e:
        logger.warning("Database query failed: %s", e)
        raise RuntimeError(f"Database unavailable: {e}") from e

