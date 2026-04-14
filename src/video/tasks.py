import asyncio
import uuid

from celery import Task

from src.worker import celery_app


@celery_app.task(bind=True, name="video.convert", max_retries=2)
def convert_video_task(
    self: Task,
    job_id: str,
    input_key: str,
    output_format: str,
    codec: str,
    crf: int,
    preset: str,
    notify_email: str | None = None,
) -> None:
    async def _run() -> None:
        from src.database import task_session
        from src.jobs.models import JobStatus
        from src.jobs.service import update_job_progress, update_job_status
        from src.notifications import send_job_completion_email
        from src.storage import storage
        from src.video.service import convert_video

        async with task_session() as db:
            try:
                await update_job_status(uuid.UUID(job_id), JobStatus.STARTED, db, celery_task_id=self.request.id)
                raw = storage.download_bytes(input_key)

                latest_pct: list[int] = [0]

                def on_progress(pct: int) -> None:
                    latest_pct[0] = pct

                convert_future = asyncio.ensure_future(
                    asyncio.to_thread(
                        convert_video,
                        raw,
                        output_format=output_format,
                        codec=codec,
                        crf=crf,
                        preset=preset,
                        on_progress=on_progress,
                    )
                )

                last_reported = 0
                while not convert_future.done():
                    await asyncio.sleep(2)
                    current = latest_pct[0]
                    if current > last_reported:
                        last_reported = current
                        await update_job_progress(uuid.UUID(job_id), current, db)

                result, mime = await convert_future
                result_key = storage.upload_bytes(result, mime, prefix="results")
                job = await update_job_status(uuid.UUID(job_id), JobStatus.COMPLETED, db, result_key=result_key)
                storage.delete_object(input_key)
                if notify_email:
                    download_url = storage.get_presigned_url(result_key) if result_key else None
                    await asyncio.to_thread(
                        send_job_completion_email,
                        notify_email,
                        job_id,
                        job.job_type.value,
                        download_url,
                    )
            except Exception as exc:
                await update_job_status(uuid.UUID(job_id), JobStatus.FAILED, db, error=str(exc))
                raise self.retry(exc=exc, countdown=120)

    asyncio.run(_run())


@celery_app.task(bind=True, name="video.rotate", max_retries=2)
def rotate_video_task(self: Task, job_id: str, input_key: str, degrees: int, no_transcode: bool, notify_email: str | None = None) -> None:
    async def _run() -> None:
        from src.database import task_session
        from src.jobs.models import JobStatus
        from src.jobs.service import update_job_status
        from src.notifications import send_job_completion_email
        from src.storage import storage
        from src.video.service import rotate_video

        async with task_session() as db:
            try:
                await update_job_status(uuid.UUID(job_id), JobStatus.STARTED, db, celery_task_id=self.request.id)
                raw = storage.download_bytes(input_key)
                result = rotate_video(raw, degrees=degrees, no_transcode=no_transcode)
                result_key = storage.upload_bytes(result, "video/mp4", prefix="results")
                job = await update_job_status(uuid.UUID(job_id), JobStatus.COMPLETED, db, result_key=result_key)
                storage.delete_object(input_key)
                if notify_email:
                    download_url = storage.get_presigned_url(result_key) if result_key else None
                    await asyncio.to_thread(send_job_completion_email, notify_email, job_id, job.job_type.value, download_url)
            except Exception as exc:
                await update_job_status(uuid.UUID(job_id), JobStatus.FAILED, db, error=str(exc))
                raise self.retry(exc=exc, countdown=120)

    asyncio.run(_run())


@celery_app.task(bind=True, name="video.resize", max_retries=2)
def resize_video_task(
    self: Task,
    job_id: str,
    input_key: str,
    width: int | None,
    height: int | None,
    keep_aspect: bool,
    notify_email: str | None = None,
) -> None:
    async def _run() -> None:
        from src.database import task_session
        from src.jobs.models import JobStatus
        from src.jobs.service import update_job_status
        from src.notifications import send_job_completion_email
        from src.storage import storage
        from src.video.service import resize_video

        async with task_session() as db:
            try:
                await update_job_status(uuid.UUID(job_id), JobStatus.STARTED, db, celery_task_id=self.request.id)
                raw = storage.download_bytes(input_key)
                result = resize_video(raw, width=width, height=height, keep_aspect=keep_aspect)
                result_key = storage.upload_bytes(result, "video/mp4", prefix="results")
                job = await update_job_status(uuid.UUID(job_id), JobStatus.COMPLETED, db, result_key=result_key)
                storage.delete_object(input_key)
                if notify_email:
                    download_url = storage.get_presigned_url(result_key) if result_key else None
                    await asyncio.to_thread(send_job_completion_email, notify_email, job_id, job.job_type.value, download_url)
            except Exception as exc:
                await update_job_status(uuid.UUID(job_id), JobStatus.FAILED, db, error=str(exc))
                raise self.retry(exc=exc, countdown=120)

    asyncio.run(_run())


@celery_app.task(bind=True, name="video.trim", max_retries=2)
def trim_video_task(self: Task, job_id: str, input_key: str, start_time: str, end_time: str, notify_email: str | None = None) -> None:
    async def _run() -> None:
        from src.database import task_session
        from src.jobs.models import JobStatus
        from src.jobs.service import update_job_status
        from src.notifications import send_job_completion_email
        from src.storage import storage
        from src.video.service import trim_video

        async with task_session() as db:
            try:
                await update_job_status(uuid.UUID(job_id), JobStatus.STARTED, db, celery_task_id=self.request.id)
                raw = storage.download_bytes(input_key)
                result = trim_video(raw, start_time=start_time, end_time=end_time)
                result_key = storage.upload_bytes(result, "video/mp4", prefix="results")
                job = await update_job_status(uuid.UUID(job_id), JobStatus.COMPLETED, db, result_key=result_key)
                storage.delete_object(input_key)
                if notify_email:
                    download_url = storage.get_presigned_url(result_key) if result_key else None
                    await asyncio.to_thread(send_job_completion_email, notify_email, job_id, job.job_type.value, download_url)
            except Exception as exc:
                await update_job_status(uuid.UUID(job_id), JobStatus.FAILED, db, error=str(exc))
                raise self.retry(exc=exc, countdown=120)

    asyncio.run(_run())


@celery_app.task(bind=True, name="video.thumbnail", max_retries=2)
def thumbnail_video_task(self: Task, job_id: str, input_key: str, timestamp: str, notify_email: str | None = None) -> None:
    async def _run() -> None:
        from src.database import task_session
        from src.jobs.models import JobStatus
        from src.jobs.service import update_job_status
        from src.notifications import send_job_completion_email
        from src.storage import storage
        from src.video.service import extract_thumbnail

        async with task_session() as db:
            try:
                await update_job_status(uuid.UUID(job_id), JobStatus.STARTED, db, celery_task_id=self.request.id)
                raw = storage.download_bytes(input_key)
                result = extract_thumbnail(raw, timestamp=timestamp)
                result_key = storage.upload_bytes(result, "image/webp", prefix="results")
                job = await update_job_status(uuid.UUID(job_id), JobStatus.COMPLETED, db, result_key=result_key)
                storage.delete_object(input_key)
                if notify_email:
                    download_url = storage.get_presigned_url(result_key) if result_key else None
                    await asyncio.to_thread(send_job_completion_email, notify_email, job_id, job.job_type.value, download_url)
            except Exception as exc:
                await update_job_status(uuid.UUID(job_id), JobStatus.FAILED, db, error=str(exc))
                raise self.retry(exc=exc, countdown=120)

    asyncio.run(_run())
