"""SQLAlchemy database engine and session factory.

The connection URL is read from application settings (DATABASE_URL). SQLite is the
local-development default; set DATABASE_URL to a PostgreSQL URL to use PostgreSQL
without changing any code.

The engine and session factory are cached as module-level singletons so that
repeated calls do not create new connection pools. Use ``reset_engine()`` in
tests to force re-initialization when DATABASE_URL changes between test cases.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from packages.core.config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None


def get_engine():
    """Return a cached SQLAlchemy engine (singleton)."""
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args = {}
        if settings.database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        _engine = create_engine(settings.database_url, connect_args=connect_args)
    return _engine


def get_session_local():
    """Return a sessionmaker bound to the cached engine.

    A new sessionmaker is returned each call (they are lightweight), but all
    share the same cached engine/connection pool so DATABASE_URL changes are
    picked up after ``reset_engine()``.
    """
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)


def reset_engine():
    """Drop the cached engine (test helper)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


def get_db():
    """Yield a SQLAlchemy session (for FastAPI dependency injection)."""
    session_local = get_session_local()
    db = session_local()
    try:
        yield db
    finally:
        db.close()
