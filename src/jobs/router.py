import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import require_active
from src.auth.models import User
from src.dependencies import get_db
from src.jobs.models import JobStatus, JobType
from src.jobs.schemas import JobListResponse, JobRead
from src.jobs.service import cancel_job, get_job_by_id, get_user_jobs
from src.storage import storage

router = APIRouter()


def _ok(data, message: str = "") -> dict:
    return {"success": True, "data": data, "message": message}


def _to_read(job) -> JobRead:
    jr = JobRead.model_validate(job)
    if job.result_key:
        try:
            jr.result_url = storage.get_presigned_url(job.result_key)
        except Exception:
            pass
    return jr


@router.get("")
async def list_jobs(
    status: JobStatus | None = Query(None),
    job_type: JobType | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_active),
    db: AsyncSession = Depends(get_db),
):
    jobs, total = await get_user_jobs(
        user_id=current_user.id,
        db=db,
        status=status,
        job_type=job_type,
        page=page,
        page_size=page_size,
    )
    return _ok(
        JobListResponse(
            items=[_to_read(j) for j in jobs],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/{job_id}")
async def get_job(
    job_id: uuid.UUID,
    current_user: User = Depends(require_active),
    db: AsyncSession = Depends(get_db),
):
    job = await get_job_by_id(job_id, current_user.id, db)
    return _ok(_to_read(job))


@router.delete("/{job_id}", status_code=204)
async def delete_job(
    job_id: uuid.UUID,
    current_user: User = Depends(require_active),
    db: AsyncSession = Depends(get_db),
):
    await cancel_job(job_id, current_user.id, db)
