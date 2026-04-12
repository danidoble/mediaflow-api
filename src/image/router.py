import magic
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import require_active
from src.auth.models import User
from src.config import settings
from src.dependencies import get_db
from src.image.exceptions import file_too_large, unsupported_image_type
from src.image.service import ALLOWED_OUTPUT_FORMATS
from src.image.tasks import convert_format_task, convert_to_avif_task, convert_to_webp_task, resize_image_task
from src.jobs.models import JobType
from src.jobs.service import create_job, update_job_status
from src.limiter import limiter
from src.storage import storage

router = APIRouter()

_ALLOWED_IMAGE_MIMES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/tiff",
    "image/bmp",
}

_MAX_BATCH_FILES = 20


async def _validate_upload(file: UploadFile, max_bytes: int) -> tuple[bytes, str]:
    data = await file.read()
    if len(data) > max_bytes:
        raise file_too_large
    mime = magic.from_buffer(data[:2048], mime=True)
    if mime not in _ALLOWED_IMAGE_MIMES:
        raise unsupported_image_type
    return data, mime


@router.post("/convert/webp", status_code=202)
@limiter.limit("30/minute")
async def convert_webp(
    request: Request,
    file: UploadFile = File(...),
    quality: int = Form(80),
    lossless: bool = Form(False),
    current_user: User = Depends(require_active),
    db: AsyncSession = Depends(get_db),
):
    data, mime = await _validate_upload(file, settings.max_upload_size_bytes)
    input_key = storage.upload_bytes(data, mime, prefix="uploads")
    job = await create_job(current_user.id, JobType.IMAGE_CONVERT_WEBP, input_key, db)
    task = convert_to_webp_task.delay(str(job.id), input_key, quality, lossless)
    await update_job_status(job.id, job.status, db, celery_task_id=task.id)
    return {"success": True, "data": {"job_id": str(job.id), "status": "pending"}, "message": "Job queued"}


@router.post("/convert/avif", status_code=202)
@limiter.limit("30/minute")
async def convert_avif(
    request: Request,
    file: UploadFile = File(...),
    quality: int = Form(60),
    current_user: User = Depends(require_active),
    db: AsyncSession = Depends(get_db),
):
    data, mime = await _validate_upload(file, settings.max_upload_size_bytes)
    input_key = storage.upload_bytes(data, mime, prefix="uploads")
    job = await create_job(current_user.id, JobType.IMAGE_CONVERT_AVIF, input_key, db)
    task = convert_to_avif_task.delay(str(job.id), input_key, quality)
    await update_job_status(job.id, job.status, db, celery_task_id=task.id)
    return {"success": True, "data": {"job_id": str(job.id), "status": "pending"}, "message": "Job queued"}


@router.post("/convert/format", status_code=202)
@limiter.limit("30/minute")
async def convert_image_format(
    request: Request,
    file: UploadFile = File(...),
    output_format: str = Form(...),
    quality: int = Form(85),
    current_user: User = Depends(require_active),
    db: AsyncSession = Depends(get_db),
):
    if output_format.lower().lstrip(".") not in ALLOWED_OUTPUT_FORMATS:
        raise HTTPException(status_code=422, detail=f"output_format must be one of: {', '.join(sorted(ALLOWED_OUTPUT_FORMATS))}")
    data, mime = await _validate_upload(file, settings.max_upload_size_bytes)
    input_key = storage.upload_bytes(data, mime, prefix="uploads")
    job = await create_job(current_user.id, JobType.IMAGE_CONVERT_FORMAT, input_key, db)
    task = convert_format_task.delay(str(job.id), input_key, output_format, quality)
    await update_job_status(job.id, job.status, db, celery_task_id=task.id)
    return {"success": True, "data": {"job_id": str(job.id), "status": "pending"}, "message": "Job queued"}


@router.post("/resize", status_code=202)
@limiter.limit("30/minute")
async def resize_image(
    request: Request,
    file: UploadFile = File(...),
    width: int | None = Form(None),
    height: int | None = Form(None),
    fit: str = Form("cover"),
    current_user: User = Depends(require_active),
    db: AsyncSession = Depends(get_db),
):
    data, mime = await _validate_upload(file, settings.max_upload_size_bytes)
    input_key = storage.upload_bytes(data, mime, prefix="uploads")
    job = await create_job(current_user.id, JobType.IMAGE_RESIZE, input_key, db)
    task = resize_image_task.delay(str(job.id), input_key, width, height, fit)
    await update_job_status(job.id, job.status, db, celery_task_id=task.id)
    return {"success": True, "data": {"job_id": str(job.id), "status": "pending"}, "message": "Job queued"}


@router.post("/batch/convert/webp", status_code=202)
@limiter.limit("10/minute")
async def batch_convert_webp(
    request: Request,
    files: list[UploadFile] = File(...),
    quality: int = Form(80),
    lossless: bool = Form(False),
    current_user: User = Depends(require_active),
    db: AsyncSession = Depends(get_db),
):
    if len(files) > _MAX_BATCH_FILES:
        raise HTTPException(status_code=422, detail=f"Maximum {_MAX_BATCH_FILES} files per batch request")
    jobs = []
    for file in files:
        data, mime = await _validate_upload(file, settings.max_upload_size_bytes)
        input_key = storage.upload_bytes(data, mime, prefix="uploads")
        job = await create_job(current_user.id, JobType.IMAGE_CONVERT_WEBP, input_key, db)
        task = convert_to_webp_task.delay(str(job.id), input_key, quality, lossless)
        await update_job_status(job.id, job.status, db, celery_task_id=task.id)
        jobs.append({"job_id": str(job.id), "filename": file.filename, "status": "pending"})
    return {"success": True, "data": {"jobs": jobs, "total": len(jobs)}, "message": f"{len(jobs)} jobs queued"}


@router.post("/batch/convert/avif", status_code=202)
@limiter.limit("10/minute")
async def batch_convert_avif(
    request: Request,
    files: list[UploadFile] = File(...),
    quality: int = Form(60),
    current_user: User = Depends(require_active),
    db: AsyncSession = Depends(get_db),
):
    if len(files) > _MAX_BATCH_FILES:
        raise HTTPException(status_code=422, detail=f"Maximum {_MAX_BATCH_FILES} files per batch request")
    jobs = []
    for file in files:
        data, mime = await _validate_upload(file, settings.max_upload_size_bytes)
        input_key = storage.upload_bytes(data, mime, prefix="uploads")
        job = await create_job(current_user.id, JobType.IMAGE_CONVERT_AVIF, input_key, db)
        task = convert_to_avif_task.delay(str(job.id), input_key, quality)
        await update_job_status(job.id, job.status, db, celery_task_id=task.id)
        jobs.append({"job_id": str(job.id), "filename": file.filename, "status": "pending"})
    return {"success": True, "data": {"jobs": jobs, "total": len(jobs)}, "message": f"{len(jobs)} jobs queued"}


@router.post("/batch/convert/format", status_code=202)
@limiter.limit("10/minute")
async def batch_convert_format(
    request: Request,
    files: list[UploadFile] = File(...),
    output_format: str = Form(...),
    quality: int = Form(85),
    current_user: User = Depends(require_active),
    db: AsyncSession = Depends(get_db),
):
    if len(files) > _MAX_BATCH_FILES:
        raise HTTPException(status_code=422, detail=f"Maximum {_MAX_BATCH_FILES} files per batch request")
    if output_format.lower().lstrip(".") not in ALLOWED_OUTPUT_FORMATS:
        raise HTTPException(status_code=422, detail=f"output_format must be one of: {', '.join(sorted(ALLOWED_OUTPUT_FORMATS))}")
    jobs = []
    for file in files:
        data, mime = await _validate_upload(file, settings.max_upload_size_bytes)
        input_key = storage.upload_bytes(data, mime, prefix="uploads")
        job = await create_job(current_user.id, JobType.IMAGE_CONVERT_FORMAT, input_key, db)
        task = convert_format_task.delay(str(job.id), input_key, output_format, quality)
        await update_job_status(job.id, job.status, db, celery_task_id=task.id)
        jobs.append({"job_id": str(job.id), "filename": file.filename, "status": "pending"})
    return {"success": True, "data": {"jobs": jobs, "total": len(jobs)}, "message": f"{len(jobs)} jobs queued"}
