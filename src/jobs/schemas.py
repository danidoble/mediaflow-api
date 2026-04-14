import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.jobs.models import JobStatus, JobType


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    status: JobStatus
    job_type: JobType
    result_url: str | None = None
    result_expired: bool = False
    progress: int | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class JobListResponse(BaseModel):
    items: list[JobRead]
    total: int
    page: int
    page_size: int
