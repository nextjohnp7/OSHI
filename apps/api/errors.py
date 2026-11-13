"""API error handling for OSHI.

Registers FastAPI exception handlers that return consistent JSON error responses
with request IDs, avoiding stack traces leaking to clients.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.responses import JSONResponse

import uuid


def _request_id(request: Request) -> str:
    return request.headers.get("x-request-id") or str(uuid.uuid4())


def _error_response(status_code: int, message: str, request: Request, detail: str | None = None) -> JSONResponse:
    body: dict[str, Any] = {
        "error": True,
        "message": message,
        "request_id": _request_id(request),
    }
    if detail is not None:
        body["detail"] = detail
    return JSONResponse(status_code=status_code, content=body)


def register_error_handlers(app: FastAPI) -> None:
    """Attach exception handlers to the FastAPI application."""

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
        return _error_response(
            500, "Database error", request, detail=str(exc)
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_error_handler(request: Request, exc: ValidationError):
        return _error_response(
            400, "Invalid request data", request, detail=exc.errors()
        )

    @app.exception_handler(RequestValidationError)
    async def fastapi_validation_error_handler(request: Request, exc: RequestValidationError):
        return _error_response(
            400, "Invalid request data", request, detail=exc.errors()
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        return _error_response(
            500, "Internal server error", request
        )
