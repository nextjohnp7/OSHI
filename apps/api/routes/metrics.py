"""Prometheus metrics endpoint.

Diekspos di GET /api/v1/metrics dalam format text/plain yang dapat di-scrape
Prometheus. Tidak menambahkan dependensi baru — metrik dihitung manual dari
state aplikasi (task store, dll.).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from packages.core.auth import require_api_key
from packages.core.tasks import task_store

router = APIRouter(prefix="/api/v1", tags=["metrics"])


def _generate_metrics() -> str:
    """Buat output metrik dalam format Prometheus text exposition."""
    lines: list[str] = []

    # Hitung task per status.
    tasks = task_store.list_tasks(limit=1000)
    status_counts: dict[str, int] = {}
    for t in tasks:
        status_counts[t["status"]] = status_counts.get(t["status"], 0) + 1

    lines.append("# HELP oshi_task_total Total number of background tasks.")
    lines.append("# TYPE oshi_task_total counter")
    for status, count in status_counts.items():
        lines.append(f'oshi_task_total{{status="{status}"}} {count}')

    lines.append("")
    lines.append("# HELP oshi_task_count Current number of background tasks by status.")
    lines.append("# TYPE oshi_task_count gauge")
    for status, count in status_counts.items():
        lines.append(f'oshi_task_count{{status="{status}"}} {count}')

    lines.append("")
    lines.append("# HELP oshi_build_info Build information.")
    lines.append("# TYPE oshi_build_info gauge")
    lines.append('oshi_build_info{version="0.1.0",service="oshi"} 1')

    return "\n".join(lines) + "\n"


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Diekspos metrik aplikasi dalam format Prometheus text exposition. "
    "Butuh API key untuk diakses.",
)
def metrics(
    current_user=Depends(require_api_key),
) -> Response:
    """Kembalikan metrik Prometheus."""
    return Response(
        content=_generate_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
