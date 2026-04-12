import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.jobs.exceptions import job_not_cancellable, job_not_found, job_not_owned
from src.jobs.models import Job, JobStatus, JobType
from src.storage import storage


async def create_job(
    user_id: uuid.UUID,
    job_type: JobType,
    input_key: str,
    db: AsyncSession,
) -> Job:
    job = Job(user_id=user_id, job_type=job_type, input_key=input_key)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def update_job_status(
    job_id: uuid.UUID,
    status: JobStatus,
    db: AsyncSession,
    result_key: str | None = None,
    error: str | None = None,
    celery_task_id: str | None = None,
) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise job_not_found

    job.status = status
    job.updated_at = datetime.utcnow()
    if result_key is not None:
        job.result_key = result_key
    if error is not None:
        job.error = error
    if celery_task_id is not None:
        job.celery_task_id = celery_task_id

    await db.commit()
    await db.refresh(job)
    return job


async def get_user_jobs(
    user_id: uuid.UUID,
    db: AsyncSession,
    status: JobStatus | None = None,
    job_type: JobType | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Job], int]:
    filters = [Job.user_id == user_id]
    if status:
        filters.append(Job.status == status)
    if job_type:
        filters.append(Job.job_type == job_type)

    count_result = await db.execute(select(func.count(Job.id)).where(*filters))
    total = count_result.scalar_one()

    jobs_result = await db.execute(
        select(Job)
        .where(*filters)
        .order_by(Job.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(jobs_result.scalars().all()), total


async def get_job_by_id(job_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise job_not_found
    if job.user_id != user_id:
        raise job_not_owned
    return job


async def cancel_job(job_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> None:
    job = await get_job_by_id(job_id, user_id, db)
    if job.status not in (JobStatus.PENDING,):
        raise job_not_cancellable

    if job.celery_task_id:
        from src.worker import celery_app
        celery_app.control.revoke(job.celery_task_id, terminate=True)

    if job.input_key:
        storage.delete_object(job.input_key)
    if job.result_key:
        storage.delete_object(job.result_key)

    job.status = JobStatus.CANCELLED
    job.updated_at = datetime.utcnow()
    await db.commit()
