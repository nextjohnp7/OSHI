"""Middleware untuk production hardening: rate limiting per API key dan CORS.

Rate limiting menggunakan in-memory sliding window (cukup untuk single-worker dev).
Untuk produksi multi-worker, ganti backend store dengan Redis.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from packages.core.auth import hash_api_key, key_prefix


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiter sederhana per API key (sliding window)."""

    def __init__(self, app, requests_per_minute: int = 60) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60.0
        # key -> list of request timestamps
        self._timestamps: dict[str, list[float]] = defaultdict(list)

    def _clean(self, key: str, now: float) -> None:
        self._timestamps[key] = [
            ts for ts in self._timestamps[key] if now - ts < self.window_seconds
        ]

    def _allowed(self, key: str, now: float) -> bool:
        self._clean(key, now)
        return len(self._timestamps[key]) < self.requests_per_minute

    def _record(self, key: str, now: float) -> None:
        self._timestamps[key].append(now)

    def _extract_api_key(self, request: Request) -> str | None:
        """Ambil API key dari header Authorization: Bearer atau X-API-Key."""
        auth = request.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            return auth.split(" ", 1)[1].strip()
        return request.headers.get("x-api-key")

    async def dispatch(self, request: Request, call_next) -> Response:
        # Hanya rate limit endpoint yang membutuhkan auth (selain /health dan /docs).
        path = request.url.path
        if path in ("/health", "/docs", "/openapi.json", "/metrics"):
            return await call_next(request)

        api_key = self._extract_api_key(request)

        # Gunakan hash API key sebagai identifier (tidak expose plaintext),
        # fallback ke client host jika tidak ada key.
        if api_key:
            identifier = f"apikey:{key_prefix(api_key)}:{hash_api_key(api_key)[:16]}"
        else:
            identifier = (
                f"host:{request.client.host}" if request.client else "anonymous"
            )
        now = time.time()

        if not self._allowed(identifier, now):
            return Response(
                content='{"detail":"Rate limit exceeded. Try again later."}',
                status_code=429,
                media_type="application/json",
            )

        self._record(identifier, now)
        return await call_next(request)


def add_cors_middleware(app, allow_origins: list[str] | None = None) -> None:
    """Tambahkan CORS middleware. Default hanya izinkan origin yang dikonfigurasi."""
    origins = allow_origins or ["http://localhost:3000", "http://127.0.0.1:3000"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )
