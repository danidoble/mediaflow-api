from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.auth.router import router as auth_router
from src.config import settings
from src.health.router import router as health_router
from src.image.router import router as image_router
from src.jobs.router import router as jobs_router
from src.limiter import limiter
from src.video.router import router as video_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.storage import storage
    storage.ensure_bucket()
    yield


app = FastAPI(
    title="MediaFlow API",
    description="Media conversion API for images and video",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_PREFIX = "/api/v1"

app.include_router(auth_router, prefix=f"{_PREFIX}/auth", tags=["auth"])
app.include_router(jobs_router, prefix=f"{_PREFIX}/jobs", tags=["jobs"])
app.include_router(image_router, prefix=f"{_PREFIX}/image", tags=["image"])
app.include_router(video_router, prefix=f"{_PREFIX}/video", tags=["video"])
app.include_router(health_router, prefix=f"{_PREFIX}/health", tags=["health"])
