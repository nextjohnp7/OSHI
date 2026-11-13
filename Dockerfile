# syntax=docker/dockerfile:1

# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install production dependencies only (no dev/test)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-group prod

# Runtime stage
FROM python:3.11-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Create non-root user
RUN useradd --create-home --shell /bin/bash oshi

# Copy virtualenv from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --chown=oshi:oshi apps/ /app/apps/
COPY --chown=oshi:oshi packages/ /app/packages/
COPY --chown=oshi:oshi alembic/ /app/alembic/
COPY --chown=oshi:oshi pyproject.toml /app/pyproject.toml

# Run migrations on startup, then launch the API
USER oshi

CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn apps.api.main:app --host 0.0.0.0 --port 8000"]
