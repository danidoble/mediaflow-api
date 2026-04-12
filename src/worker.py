from celery import Celery

from src.config import settings

# Register all SQLModel table classes in the shared metadata so SQLAlchemy
# can resolve FK relationships (e.g. jobs.user_id -> users.id) inside the
# worker process, where the API models are never imported otherwise.
from src.auth.models import User  # noqa: F401
from src.jobs.models import Job  # noqa: F401

# Redis can be replaced with RabbitMQ by changing CELERY_BROKER_URL to amqp://
celery_app = Celery(
    "mediaflow",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "src.image.tasks",
        "src.video.tasks",
        "src.jobs.tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "cleanup-expired-jobs": {
            "task": "src.jobs.tasks.cleanup_expired_jobs",
            "schedule": 3600.0,
        },
    },
)
