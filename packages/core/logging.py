"""Structured logging configuration for OSHI.

Configures Python's stdlib logging with JSON output for production and human-readable
output for development. All OSHI modules should use ``logging.getLogger(__name__)``.
"""

import logging
import sys
from typing import Any


def configure_logging(log_level: str = "INFO") -> None:
    """Configure root logger with a JSON or plain formatter.

    In production (non-debug), logs are emitted as JSON lines for easy ingestion by
    log collectors. In development, plain text is used for readability.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)

    try:
        import pythonjsonlogger.jsonlogger as jsonlogger  # type: ignore

        formatter: logging.Formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s"
        )
    except ImportError:  # pragma: no cover - fallback when jsonlogger not installed
        formatter = logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
        )

    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    # Avoid duplicate handlers if configure_logging is called multiple times.
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(handler)

    # Quieten noisy third-party loggers.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
