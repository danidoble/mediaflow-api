from pydantic import BaseModel, Field


class VideoConvertOptions(BaseModel):
    output_format: str = Field(default="mp4", pattern="^(mp4|webm|mkv)$")
    codec: str = Field(default="libx264")
    crf: int = Field(default=23, ge=0, le=51)
    preset: str = Field(default="medium")


class VideoRotateOptions(BaseModel):
    degrees: int = Field(default=90, description="Rotation in degrees: 90, 180 or 270")
    no_transcode: bool = Field(default=False, description="Rotate via metadata flag, skip re-encoding")


class VideoResizeOptions(BaseModel):
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    keep_aspect: bool = True


class VideoTrimOptions(BaseModel):
    start_time: str = Field(description="Start time HH:MM:SS or seconds")
    end_time: str = Field(description="End time HH:MM:SS or seconds")


class VideoThumbnailOptions(BaseModel):
    timestamp: str = Field(default="00:00:01", description="Frame timestamp HH:MM:SS")
