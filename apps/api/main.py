"""FastAPI application factory and routes.

Foundation endpoints:
- GET /health — health check and database connectivity.
- POST /api/v1/publications/search — search OpenAlex, normalize, store.
- GET /api/v1/publications — search stored publications.
- GET /api/v1/publications/{id} — get a stored publication.
"""

from fastapi import FastAPI

from apps.api.routes.publications import router as publications_router
from packages.core.config import get_settings
from packages.core.database import get_engine
from sqlalchemy import text


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug)

    app.include_router(publications_router)

    @app.get("/health", response_model=dict)
    def health():
        """Return service status and database connectivity."""
        db_ok = False
        db_error = None
        try:
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_ok = True
        except Exception as exc:  # noqa: BLE001 — report connectivity failure
            db_error = str(exc)

        return {
            "status": "ok" if db_ok else "degraded",
            "service": settings.app_name,
            "env": settings.app_env,
            "database": "connected" if db_ok else "disconnected",
            "database_error": db_error,
        }

    return app


app = create_app()
