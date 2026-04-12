import magic
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import require_active
from src.auth.models import User
from src.config import settings
from src.dependencies import get_db
from src.jobs.models import JobType
from src.jobs.service import create_job, update_job_status
from src.limiter import limiter
from src.storage import storage
from src.video.exceptions import file_too_large, invalid_rotation_degrees, unsupported_video_type
from src.video.tasks import (
    convert_video_task,
    resize_video_task,
    rotate_video_task,
    thumbnail_video_task,
    trim_video_task,
)

router = APIRouter()

_ALLOWED_VIDEO_MIMES = {
    "video/mp4",
    "video/webm",
    "video/x-matroska",
    "video/quicktime",
    "video/x-msvideo",
    "video/mpeg",
    "video/ogg",
    "video/3gpp",
}


async def _validate_upload(file: UploadFile, max_bytes: int) -> tuple[bytes, str]:
    data = await file.read()
    if len(data) > max_bytes:
        raise file_too_large
    mime = magic.from_buffer(data[:2048], mime=True)
    if mime not in _ALLOWED_VIDEO_MIMES:
        raise unsupported_video_type
    return data, mime


@router.post("/convert", status_code=202)
@limiter.limit("10/minute")
async def convert_video(
    request: Request,
    file: UploadFile = File(...),
    output_format: str = Form("mp4"),
    codec: str = Form("libx264"),
    crf: int = Form(23),
    preset: str = Form("medium"),
    current_user: User = Depends(require_active),
    db: AsyncSession = Depends(get_db),
):
    data, mime = await _validate_upload(file, settings.max_upload_size_bytes)
    input_key = storage.upload_bytes(data, mime, prefix="uploads")
    job = await create_job(current_user.id, JobType.VIDEO_CONVERT, input_key, db)
    task = convert_video_task.delay(str(job.id), input_key, output_format, codec, crf, preset)
    await update_job_status(job.id, job.status, db, celery_task_id=task.id)
    return {"success": True, "data": {"job_id": str(job.id), "status": "pending"}, "message": "Job queued"}


@router.post("/rotate", status_code=202)
@limiter.limit("10/minute")
async def rotate_video(
    request: Request,
    file: UploadFile = File(...),
    degrees: int = Form(90),
    no_transcode: bool = Form(False),
    current_user: User = Depends(require_active),
    db: AsyncSession = Depends(get_db),
):
    if degrees not in (90, 180, 270):
        raise invalid_rotation_degrees
    data, mime = await _validate_upload(file, settings.max_upload_size_bytes)
    input_key = storage.upload_bytes(data, mime, prefix="uploads")
    job = await create_job(current_user.id, JobType.VIDEO_ROTATE, input_key, db)
    task = rotate_video_task.delay(str(job.id), input_key, degrees, no_transcode)
    await update_job_status(job.id, job.status, db, celery_task_id=task.id)
    return {"success": True, "data": {"job_id": str(job.id), "status": "pending"}, "message": "Job queued"}


@router.post("/resize", status_code=202)
@limiter.limit("10/minute")
async def resize_video(
    request: Request,
    file: UploadFile = File(...),
    width: int | None = Form(None),
    height: int | None = Form(None),
    keep_aspect: bool = Form(True),
    current_user: User = Depends(require_active),
    db: AsyncSession = Depends(get_db),
):
    data, mime = await _validate_upload(file, settings.max_upload_size_bytes)
    input_key = storage.upload_bytes(data, mime, prefix="uploads")
    job = await create_job(current_user.id, JobType.VIDEO_RESIZE, input_key, db)
    task = resize_video_task.delay(str(job.id), input_key, width, height, keep_aspect)
    await update_job_status(job.id, job.status, db, celery_task_id=task.id)
    return {"success": True, "data": {"job_id": str(job.id), "status": "pending"}, "message": "Job queued"}


@router.post("/trim", status_code=202)
@limiter.limit("10/minute")
async def trim_video(
    request: Request,
    file: UploadFile = File(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    current_user: User = Depends(require_active),
    db: AsyncSession = Depends(get_db),
):
    data, mime = await _validate_upload(file, settings.max_upload_size_bytes)
    input_key = storage.upload_bytes(data, mime, prefix="uploads")
    job = await create_job(current_user.id, JobType.VIDEO_TRIM, input_key, db)
    task = trim_video_task.delay(str(job.id), input_key, start_time, end_time)
    await update_job_status(job.id, job.status, db, celery_task_id=task.id)
    return {"success": True, "data": {"job_id": str(job.id), "status": "pending"}, "message": "Job queued"}


@router.post("/thumbnail", status_code=202)
@limiter.limit("20/minute")
async def video_thumbnail(
    request: Request,
    file: UploadFile = File(...),
    timestamp: str = Form("00:00:01"),
    current_user: User = Depends(require_active),
    db: AsyncSession = Depends(get_db),
):
    data, mime = await _validate_upload(file, settings.max_upload_size_bytes)
    input_key = storage.upload_bytes(data, mime, prefix="uploads")
    job = await create_job(current_user.id, JobType.VIDEO_THUMBNAIL, input_key, db)
    task = thumbnail_video_task.delay(str(job.id), input_key, timestamp)
    await update_job_status(job.id, job.status, db, celery_task_id=task.id)
    return {"success": True, "data": {"job_id": str(job.id), "status": "pending"}, "message": "Job queued"}
