import uuid
from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel
from typing import Optional


class JobStatus(str, Enum):
    PENDING = "pending"
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    IMAGE_CONVERT_WEBP = "image_convert_webp"
    IMAGE_CONVERT_AVIF = "image_convert_avif"
    IMAGE_CONVERT_FORMAT = "image_convert_format"
    IMAGE_RESIZE = "image_resize"
    VIDEO_CONVERT = "video_convert"
    VIDEO_ROTATE = "video_rotate"
    VIDEO_RESIZE = "video_resize"
    VIDEO_TRIM = "video_trim"
    VIDEO_THUMBNAIL = "video_thumbnail"


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(index=True, foreign_key="users.id")
    status: JobStatus = Field(default=JobStatus.PENDING)
    job_type: JobType
    input_key: str | None = None
    result_key: str | None = None
    error: str | None = None
    celery_task_id: str | None = None
    progress: Optional[int] = Field(default=None, nullable=True)
    expires_at: Optional[datetime] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
