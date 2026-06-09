"""Celery application for background jobs."""
from urllib.parse import quote

from app.config import settings


def _redis_url(db: int | None = None) -> str:
    selected_db = settings.REDIS_DB if db is None else db
    password = f":{quote(settings.REDIS_PASSWORD, safe='')}@" if settings.REDIS_PASSWORD else ""
    return f"redis://{password}{settings.REDIS_HOST}:{settings.REDIS_PORT}/{selected_db}"


try:
    from celery import Celery

    celery_app = Celery(
        "campus_agent",
        broker=_redis_url(settings.REDIS_DB),
        backend=_redis_url(settings.REDIS_DB),
        include=["app.tasks.knowledge_tasks"],
    )
    celery_app.conf.update(
        task_track_started=True,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="Asia/Shanghai",
        enable_utc=False,
        worker_prefetch_multiplier=1,
        task_acks_late=True,
    )
except ImportError:
    celery_app = None
