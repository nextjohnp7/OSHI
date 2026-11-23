"""Celery application for durable background jobs (P1: persistent queue).

Reads broker/result backend from ``Settings`` (``CELERY_BROKER_URL`` /
``CELERY_RESULT_BACKEND`` env vars). Worker commands:

    celery -A packages.core.celery_app.celery_app worker --loglevel=info
    celery -A packages.core.celery_app.celery_app beat --loglevel=info
"""

from celery import Celery

from packages.core.config import get_settings

_settings = get_settings()

# Gunakan URL yang sudah mengandung password (mis. dari CELERY_BROKER_URL
# langsung), atau bangun dari redis_password jika hanya password saja yang diatur.
celery_app = Celery(
    "oshi",
    broker=_settings.broker_url_with_password,
    backend=_settings.backend_url_with_password,
    include=[
        "packages.worker.ingest_tasks",
        "packages.worker.research_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_max_tasks_per_child=50,
    worker_prefetch_multiplier=1,
    result_expires=3600,
)
