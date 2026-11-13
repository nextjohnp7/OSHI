"""SQLAlchemy database engine and session factory.

The connection URL is read from application settings (DATABASE_URL). SQLite is the
local-development default; set DATABASE_URL to a PostgreSQL URL to use PostgreSQL
without changing any code.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from packages.core.config import get_settings


class Base(DeclarativeBase):
    pass


def get_engine():
    settings = get_settings()
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(settings.database_url, connect_args=connect_args)


def get_session_local():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)


def get_db():
    """Yield a SQLAlchemy session (for FastAPI dependency injection)."""
    session_local = get_session_local()
    db = session_local()
    try:
        yield db
    finally:
        db.close()
