"""
Celery application configuration
"""

from celery import Celery
from app.config import settings

celery_app = Celery(
    "browser_tests",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max per task
    task_soft_time_limit=540,  # Soft limit at 9 minutes
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_concurrency=4,  # 4 concurrent workers
)

# Task routes
celery_app.conf.task_routes = {
    "app.workers.tasks.execute_browser_test": {"queue": "browser_tests"},
}
