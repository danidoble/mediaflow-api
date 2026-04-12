import asyncio
import uuid
from datetime import datetime, timedelta

from src.worker import celery_app


@celery_app.task(name="src.jobs.tasks.cleanup_expired_jobs")
def cleanup_expired_jobs() -> None:
    """Delete completed/failed/cancelled jobs older than 7 days and their stored files."""

    async def _run() -> None:
        from sqlalchemy import select

        from src.database import async_session_factory
        from src.jobs.models import Job, JobStatus
        from src.storage import storage

        cutoff = datetime.utcnow() - timedelta(days=7)
        async with async_session_factory() as db:
            result = await db.execute(
                select(Job).where(
                    Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]),
                    Job.created_at < cutoff,
                )
            )
            jobs = result.scalars().all()
            for job in jobs:
                if job.input_key:
                    storage.delete_object(job.input_key)
                if job.result_key:
                    storage.delete_object(job.result_key)
                await db.delete(job)
            await db.commit()

    asyncio.run(_run())
