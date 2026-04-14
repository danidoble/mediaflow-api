import subprocess

from fastapi import APIRouter
from sqlalchemy import text

router = APIRouter()


@router.get("")
async def health():
    results: dict[str, str] = {}

    # Database
    try:
        from src.database import engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        results["database"] = "ok"
    except Exception as exc:
        results["database"] = f"error: {exc}"

    # Redis
    try:
        import redis as _redis
        from src.config import settings
        r = _redis.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
        results["redis"] = "ok"
    except Exception as exc:
        results["redis"] = f"error: {exc}"

    # MinIO
    try:
        from src.storage import storage
        if storage.health_check():
            results["minio"] = "ok"
        else:
            results["minio"] = "error: unreachable"
    except Exception as exc:
        results["minio"] = f"error: {exc}"

    # ffmpeg
    try:
        proc = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        results["ffmpeg"] = "ok" if proc.returncode == 0 else "error: non-zero exit"
    except Exception as exc:
        results["ffmpeg"] = f"error: {exc}"

    # cwebp
    try:
        proc = subprocess.run(["cwebp", "-version"], capture_output=True, timeout=5)
        results["cwebp"] = "ok" if proc.returncode == 0 else "error: non-zero exit"
    except Exception as exc:
        results["cwebp"] = f"error: {exc}"

    # Email / SMTP
    try:
        from src.config import settings as _settings
        if _settings.smtp_host:
            results["email"] = "ok"
        else:
            results["email"] = "not configured"
    except Exception as exc:
        results["email"] = f"error: {exc}"

    all_ok = all(v == "ok" for v in results.values())
    return {
        "success": all_ok,
        "data": results,
        "message": "All systems operational" if all_ok else "Some dependencies are unavailable",
    }
