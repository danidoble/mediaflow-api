import asyncio
import uuid
from datetime import datetime, timedelta

from src.worker import celery_app


@celery_app.task(name="src.jobs.tasks.cleanup_expired_jobs")
def cleanup_expired_jobs() -> None:
    """Phase 1: delete result files whose 24h TTL has elapsed.
    Phase 2: permanently delete job records older than 7 days."""

    async def _run() -> None:
        from sqlalchemy import select

        from src.database import async_session_factory
        from src.jobs.models import Job, JobStatus
        from src.storage import storage

        now = datetime.utcnow()
        old_cutoff = now - timedelta(days=7)

        async with async_session_factory() as db:
            # Phase 1: expire result files after 24 h
            expired_result = await db.execute(
                select(Job).where(
                    Job.expires_at.isnot(None),
                    Job.expires_at <= now,
                    Job.result_key.isnot(None),
                )
            )
            for job in expired_result.scalars().all():
                storage.delete_object(job.result_key)
                job.result_key = None
                job.updated_at = now
            await db.commit()

            # Phase 2: delete old job records entirely
            old_result = await db.execute(
                select(Job).where(
                    Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]),
                    Job.created_at < old_cutoff,
                )
            )
            for job in old_result.scalars().all():
                if job.input_key:
                    storage.delete_object(job.input_key)
                if job.result_key:
                    storage.delete_object(job.result_key)
                await db.delete(job)
            await db.commit()

    asyncio.run(_run())
