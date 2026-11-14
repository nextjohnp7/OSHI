"""FastAPI application factory and routes.

Foundation endpoints:
- GET /health — health check and database connectivity.
- POST /api/v1/publications/search — search OpenAlex, normalize, store.
- GET /api/v1/publications — search stored publications.
- GET /api/v1/publications/{id} — get a stored publication.
"""

from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from apps.api.errors import register_error_handlers
from apps.api.routes.admin import router as admin_router
from apps.api.routes.agents import router as agents_router
from apps.api.routes.metrics import router as metrics_router
from apps.api.routes.tasks import router as tasks_router
from apps.api.routes.auth import router as auth_router
from apps.api.routes.crisis import router as crisis_router, warnings_router
from apps.api.routes.documents import router as documents_router
from apps.api.routes.publications import router as publications_router
from apps.api.routes.research import router as research_router
from packages.core.auth import require_api_key
from packages.core.config import get_settings
from packages.core.database import get_engine
from packages.core.logging import configure_logging, get_logger
from packages.core.middleware import RateLimitMiddleware, add_cors_middleware
from packages.core.tasks import task_store
from sqlalchemy import text


logger = get_logger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(log_level="DEBUG" if settings.debug else "INFO")
    app = FastAPI(title=settings.app_name, debug=settings.debug)

    register_error_handlers(app)
    add_cors_middleware(app)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=60)
    app.include_router(auth_router)
    app.include_router(
        publications_router,
        dependencies=[Depends(require_api_key)],
    )
    app.include_router(
        documents_router,
        dependencies=[Depends(require_api_key)],
    )
    app.include_router(
        research_router,
        dependencies=[Depends(require_api_key)],
    )
    app.include_router(
        crisis_router,
        dependencies=[Depends(require_api_key)],
    )
    app.include_router(
        warnings_router,
        dependencies=[Depends(require_api_key)],
    )
    app.include_router(
        agents_router,
        dependencies=[Depends(require_api_key)],
    )
    app.include_router(
        admin_router,
        dependencies=[Depends(require_api_key)],
    )
    app.include_router(
        tasks_router,
        dependencies=[Depends(require_api_key)],
    )
    app.include_router(
        metrics_router,
        dependencies=[Depends(require_api_key)],
    )

    @app.get("/health", response_model=dict)
    def health(request: Request):
        """Return service status and database connectivity (detailed)."""
        logger.debug("health check requested")
        db_ok = False
        db_error = None
        try:
            engine = get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_ok = True
        except Exception as exc:  # noqa: BLE001 — report connectivity failure
            db_error = str(exc)
            logger.error("health check database failure: %s", exc)

        # Hitung task pending sebagai indikator beban antrean.
        pending_tasks = 0
        try:
            pending_tasks = sum(
                1 for t in task_store.list_tasks(limit=1000) if t["status"] == "pending"
            )
        except Exception:  # noqa: BLE001 — non-fatal for health
            pending_tasks = -1

        return {
            "status": "ok" if db_ok else "degraded",
            "service": settings.app_name,
            "env": settings.app_env,
            "database": "connected" if db_ok else "disconnected",
            "database_error": db_error,
            "pending_tasks": pending_tasks,
        }

    # Serve frontend MVP
    web_dir = Path(__file__).resolve().parent.parent.parent / "web"
    if web_dir.exists():
        app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")

        @app.get("/", response_class=FileResponse)
        async def frontend_root():
            return FileResponse(str(web_dir / "index.html"))

    return app


app = create_app()
