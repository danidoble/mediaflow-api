import asyncio
import uuid

from celery import Task

from src.worker import celery_app


@celery_app.task(bind=True, name="image.convert_webp", max_retries=3)
def convert_to_webp_task(self: Task, job_id: str, input_key: str, quality: int, lossless: bool) -> None:
    async def _run() -> None:
        from src.database import task_session
        from src.image.service import convert_to_webp
        from src.jobs.models import JobStatus
        from src.jobs.service import update_job_status
        from src.storage import storage

        async with task_session() as db:
            try:
                await update_job_status(uuid.UUID(job_id), JobStatus.STARTED, db, celery_task_id=self.request.id)
                raw = storage.download_bytes(input_key)
                result = convert_to_webp(raw, quality=quality, lossless=lossless)
                result_key = storage.upload_bytes(result, "image/webp", prefix="results")
                await update_job_status(uuid.UUID(job_id), JobStatus.COMPLETED, db, result_key=result_key)
            except Exception as exc:
                await update_job_status(uuid.UUID(job_id), JobStatus.FAILED, db, error=str(exc))
                raise self.retry(exc=exc, countdown=60)

    asyncio.run(_run())


@celery_app.task(bind=True, name="image.convert_avif", max_retries=3)
def convert_to_avif_task(self: Task, job_id: str, input_key: str, quality: int) -> None:
    async def _run() -> None:
        from src.database import task_session
        from src.image.service import convert_to_avif
        from src.jobs.models import JobStatus
        from src.jobs.service import update_job_status
        from src.storage import storage

        async with task_session() as db:
            try:
                await update_job_status(uuid.UUID(job_id), JobStatus.STARTED, db, celery_task_id=self.request.id)
                raw = storage.download_bytes(input_key)
                result = convert_to_avif(raw, quality=quality)
                result_key = storage.upload_bytes(result, "image/avif", prefix="results")
                await update_job_status(uuid.UUID(job_id), JobStatus.COMPLETED, db, result_key=result_key)
            except Exception as exc:
                await update_job_status(uuid.UUID(job_id), JobStatus.FAILED, db, error=str(exc))
                raise self.retry(exc=exc, countdown=60)

    asyncio.run(_run())


@celery_app.task(bind=True, name="image.convert_format", max_retries=3)
def convert_format_task(self: Task, job_id: str, input_key: str, output_format: str, quality: int) -> None:
    async def _run() -> None:
        from src.database import task_session
        from src.image.service import convert_format
        from src.jobs.models import JobStatus
        from src.jobs.service import update_job_status
        from src.storage import storage

        async with task_session() as db:
            try:
                await update_job_status(uuid.UUID(job_id), JobStatus.STARTED, db, celery_task_id=self.request.id)
                raw = storage.download_bytes(input_key)
                result, mime = convert_format(raw, output_format=output_format, quality=quality)
                result_key = storage.upload_bytes(result, mime, prefix="results")
                await update_job_status(uuid.UUID(job_id), JobStatus.COMPLETED, db, result_key=result_key)
            except Exception as exc:
                await update_job_status(uuid.UUID(job_id), JobStatus.FAILED, db, error=str(exc))
                raise self.retry(exc=exc, countdown=60)

    asyncio.run(_run())


@celery_app.task(bind=True, name="image.resize", max_retries=3)
def resize_image_task(
    self: Task,
    job_id: str,
    input_key: str,
    width: int | None,
    height: int | None,
    fit: str,
) -> None:
    async def _run() -> None:
        from src.database import task_session
        from src.image.service import resize_image
        from src.jobs.models import JobStatus
        from src.jobs.service import update_job_status
        from src.storage import storage

        async with task_session() as db:
            try:
                await update_job_status(uuid.UUID(job_id), JobStatus.STARTED, db, celery_task_id=self.request.id)
                raw = storage.download_bytes(input_key)
                result = resize_image(raw, width=width, height=height, fit=fit)
                result_key = storage.upload_bytes(result, "image/webp", prefix="results")
                await update_job_status(uuid.UUID(job_id), JobStatus.COMPLETED, db, result_key=result_key)
            except Exception as exc:
                await update_job_status(uuid.UUID(job_id), JobStatus.FAILED, db, error=str(exc))
                raise self.retry(exc=exc, countdown=60)

    asyncio.run(_run())
