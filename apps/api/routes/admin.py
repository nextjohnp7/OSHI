"""Administration API routes.

Endpoints:
- GET /api/v1/admin/health — detailed system health
- GET /api/v1/admin/version — version and build information
- GET /api/v1/admin/routes — list registered API routes

These endpoints require API key authentication and are intended for
operational monitoring and debugging (Part 10 /api/v1/admin/).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.routing import APIRoute

from packages.core.auth import require_api_key
from packages.core.config import get_settings

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

__version__ = "0.1.0"


@router.get("/health", response_model=dict[str, Any])
def admin_health(
    request: Request,
    current_user=Depends(require_api_key),
) -> dict[str, Any]:
    """Detailed system health for operators."""
    routes = []
    for route in request.app.routes:
        if isinstance(route, APIRoute):
            routes.append(
                {
                    "path": route.path,
                    "methods": sorted(list(route.methods)) if route.methods else [],
                    "name": route.name,
                }
            )
    return {
        "status": "ok",
        "service": get_settings().app_name,
        "env": get_settings().app_env,
        "version": __version__,
        "route_count": len(routes),
        "routes": routes,
    }


@router.get("/version", response_model=dict[str, str])
def admin_version(
    current_user=Depends(require_api_key),
) -> dict[str, str]:
    """Return version and build information."""
    return {
        "version": __version__,
        "service": get_settings().app_name,
    }


@router.get("/routes", response_model=list[dict[str, Any]])
def admin_routes(
    request: Request,
    current_user=Depends(require_api_key),
) -> list[dict[str, Any]]:
    """List all registered API routes."""
    out = []
    for route in request.app.routes:
        if isinstance(route, APIRoute):
            out.append(
                {
                    "path": route.path,
                    "methods": sorted(list(route.methods)) if route.methods else [],
                    "name": route.name,
                }
            )
    return sorted(out, key=lambda r: r["path"])
