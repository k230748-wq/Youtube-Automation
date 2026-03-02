"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab
from config.settings import settings

celery = Celery(
    "youtube-automation",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=3600,
    task_time_limit=4200,
    beat_schedule={
        "discover-ideas-daily": {
            "task": "worker.scheduled.discover_ideas_all_channels",
            "schedule": crontab(hour=6, minute=0),  # Daily at 6 AM UTC
        },
        "cleanup-stale-pipelines": {
            "task": "worker.scheduled.cleanup_stale_pipelines",
            "schedule": crontab(minute=0, hour="*/2"),  # Every 2 hours
        },
        "cleanup-old-assets": {
            "task": "worker.scheduled.cleanup_old_assets",
            "schedule": crontab(hour=3, minute=0, day_of_week=0),  # Weekly Sunday 3 AM
        },
    },
)

celery.autodiscover_tasks(["worker"])
