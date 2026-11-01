"""Celery app + beat schedule (PRD §6.3 BE-ING-6). Shares code with the API.

    celery -A app.worker.celery_app worker -l info
    celery -A app.worker.celery_app beat -l info

In DEMO mode the sim clock drives everything, so scheduled ingest tasks only
record that the scenario adapter is serving data. Live adapters land with the
ingestion milestone.
"""

from __future__ import annotations

from datetime import UTC, datetime

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select

from app.config import get_settings

settings = get_settings()
celery = Celery("drishti", broker=settings.redis_url, backend=settings.redis_url)
celery.conf.timezone = "Asia/Kolkata"
celery.conf.beat_schedule = {
    "weather-hourly": {"task": "drishti.ingest", "schedule": crontab(minute=5), "args": ("weather",)},
    "gauges-30min": {"task": "drishti.ingest", "schedule": crontab(minute="*/30"), "args": ("gauges",)},
    "sachet-10min": {"task": "drishti.ingest", "schedule": crontab(minute="*/10"), "args": ("sachet",)},
    "risk-hourly": {"task": "drishti.recompute", "schedule": crontab(minute=10)},
}


@celery.task(name="drishti.ingest")
def ingest(source: str) -> dict:
    from app import models as m
    from app.db import session_factory

    with session_factory()() as db:
        row = db.scalar(select(m.DataSource).where(m.DataSource.key == source))
        if row is None:
            return {"source": source, "status": "unknown_source"}
        if row.adapter == "scenario":
            row.last_success_at = datetime.now(UTC)
            row.last_error = None
            db.commit()
            return {"source": source, "status": "scenario"}
        return {"source": source, "status": "adapter_not_implemented", "adapter": row.adapter}


@celery.task(name="drishti.recompute")
def recompute() -> dict:
    """Live-mode hourly recompute. In DEMO mode the API's sim clock recomputes on each tick."""
    if settings.is_demo:
        return {"status": "skipped_demo"}
    return {"status": "live_recompute_not_implemented"}
