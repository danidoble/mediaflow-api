from pydantic import BaseModel, Field


class WebPConvertOptions(BaseModel):
    quality: int = Field(default=80, ge=0, le=100)
    lossless: bool = False


class AVIFConvertOptions(BaseModel):
    quality: int = Field(default=60, ge=0, le=63)


class ImageResizeOptions(BaseModel):
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    fit: str = Field(default="cover", pattern="^(cover|contain|fill)$")
