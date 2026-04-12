You are an expert Python backend engineer. Generate a complete, production-ready 
FastAPI project for a media conversion API (images and video) with the following 
specifications:

---

## PROJECT OVERVIEW

A RESTful API that accepts image and video files, processes them using CLI tools 
(cwebp, ffmpeg), and returns converted/manipulated results. Everything runs inside 
Docker Compose. No frontend needed — pure API consumed by web, mobile, or CLI clients.

---

## TECH STACK

- **Python 3.12+**
- **FastAPI** (async, APIRouter, dependency injection)
- **UV** as package manager (pyproject.toml, NO requirements.txt)
- **Docker Compose** (multi-service, production-ready)
- **cwebp** (libwebp-tools) for image → WebP conversion
- **ffmpeg** for video operations
- **Celery + Redis** for async job queue (long conversions run in background)
- **PostgreSQL** for job tracking and user data
- **SQLModel** (SQLAlchemy + Pydantic combined) for ORM
- **Alembic** for DB migrations
- **JWT authentication** (OAuth2 password flow, access + refresh tokens)
- **MinIO** (S3-compatible) for file storage (input uploads + output files)

---

## ARCHITECTURE & FOLDER STRUCTURE

Use domain-driven modular structure (NOT file-type based):

media-converter/
├── docker-compose.yml
├── docker-compose.override.yml        # dev overrides (hot reload, ports)
├── Dockerfile
├── pyproject.toml                     # UV-managed dependencies
├── alembic/
│   ├── env.py
│   └── versions/
├── src/
│   ├── main.py                        # FastAPI app factory
│   ├── config.py                      # Settings via pydantic-settings + .env
│   ├── database.py                    # Async SQLAlchemy engine + session
│   ├── dependencies.py                # Shared DI: db session, current user
│   ├── storage.py                     # MinIO client wrapper
│   ├── worker.py                      # Celery app instance
│   │
│   ├── auth/
│   │   ├── router.py                  # POST /api/v1/auth/register, /login, /refresh
│   │   ├── schemas.py
│   │   ├── models.py                  # User SQLModel
│   │   ├── service.py                 # register, login, token logic
│   │   ├── dependencies.py            # get_current_user, require_active
│   │   ├── security.py                # JWT encode/decode, password hashing
│   │   └── exceptions.py
│   │
│   ├── jobs/
│   │   ├── router.py                  # GET /api/v1/jobs, GET /api/v1/jobs/{id}
│   │   ├── schemas.py                 # JobCreate, JobRead, JobStatus enum
│   │   ├── models.py                  # Job SQLModel (id, user_id, status, type, result_url, error)
│   │   ├── service.py                 # create_job, update_job_status, get_user_jobs
│   │   └── exceptions.py
│   │
│   ├── image/
│   │   ├── router.py                  # POST /api/v1/image/convert/webp, /resize, /convert/avif
│   │   ├── schemas.py                 # ImageConvertRequest, options per operation
│   │   ├── tasks.py                   # Celery tasks: convert_to_webp_task, resize_image_task
│   │   ├── service.py                 # subprocess calls to cwebp, ImageMagick
│   │   └── exceptions.py
│   │
│   ├── video/
│   │   ├── router.py                  # POST /api/v1/video/convert, /rotate, /resize, /trim, /thumbnail
│   │   ├── schemas.py                 # VideoConvertRequest, RotateRequest, TrimRequest, etc.
│   │   ├── tasks.py                   # Celery tasks wrapping ffmpeg commands
│   │   ├── service.py                 # ffmpeg subprocess builder (no ffmpeg-python lib, raw subprocess)
│   │   └── exceptions.py
│   │
│   └── health/
│       └── router.py                  # GET /api/v1/health (checks db, redis, minio, ffmpeg, cwebp)
│
└── tests/
├── conftest.py
├── test_auth.py
├── test_image.py
└── test_video.py

---

## API DESIGN

All routes under `/api/v1/` prefix. All responses follow a consistent envelope:

```json
{
  "success": true,
  "data": { ... },
  "message": "string"
}
```

Errors follow RFC 7807 problem detail format.

### Auth endpoints
- `POST /api/v1/auth/register` — email + password, returns tokens
- `POST /api/v1/auth/login` — OAuth2 form, returns access + refresh JWT
- `POST /api/v1/auth/refresh` — rotate refresh token
- `GET  /api/v1/auth/me` — current user info

### Image endpoints (all require Bearer token)
- `POST /api/v1/image/convert/webp` — multipart upload, options: quality (int), lossless (bool)
- `POST /api/v1/image/convert/avif` — via ffmpeg or pillow-avif
- `POST /api/v1/image/resize` — options: width, height, fit (cover|contain|fill)

### Video endpoints (all require Bearer token)
- `POST /api/v1/video/convert` — options: output_format (mp4|webm|mkv), codec, crf, preset
- `POST /api/v1/video/rotate` — options: degrees (90|180|270), no_transcode (bool, use metadata rotate)
- `POST /api/v1/video/resize` — options: width, height, keep_aspect (bool)
- `POST /api/v1/video/trim` — options: start_time (str HH:MM:SS), end_time (str)
- `POST /api/v1/video/thumbnail` — extract frame at timestamp, returns WebP image

### Jobs endpoints
- `GET /api/v1/jobs` — list user's jobs (paginated), filter by status/type
- `GET /api/v1/jobs/{job_id}` — job detail + result download URL (presigned MinIO URL)
- `DELETE /api/v1/jobs/{job_id}` — cancel pending job, delete files

### Health
- `GET /api/v1/health` — returns status of all dependencies

---

## JOB FLOW (async pattern)

1. Client uploads file → endpoint validates schema → uploads raw file to MinIO
2. Creates Job record in DB (status: PENDING)
3. Dispatches Celery task with job_id
4. Returns `202 Accepted` with `{ job_id, status: "pending" }`
5. Celery worker: downloads from MinIO → runs cwebp/ffmpeg → uploads result to MinIO → updates Job (status: COMPLETED, result_key)
6. Client polls `GET /api/v1/jobs/{job_id}` or (optional) receives webhook
7. On COMPLETED: job response includes presigned download URL (expires in 1h)

---

## DOCKER COMPOSE SERVICES

```yaml
services:
  api:          # FastAPI + uvicorn, 2 workers
  worker:       # Celery worker (same image, different CMD)
  beat:         # Celery beat for scheduled cleanup tasks
  db:           # PostgreSQL 16
  redis:        # Redis 7 (Celery broker + result backend)
  minio:        # MinIO latest (S3-compatible storage)
  minio-init:   # One-shot container: creates buckets on first run
```

The api and worker services use the SAME Dockerfile. Entrypoint differs via CMD.
Include resource limits (cpu, memory) on worker service — this is where ffmpeg runs.
Include a `deploy.replicas` comment showing how to scale workers horizontally.

---

## DOCKERFILE REQUIREMENTS

- Base: `python:3.12-slim`
- Install system packages: `ffmpeg`, `libwebp-tools` (provides cwebp), `libmagic1`
- Install UV, use `uv sync --frozen` to install Python deps
- Non-root user for security
- Multi-stage build: builder stage installs deps, final stage copies venv
- HEALTHCHECK using the `/api/v1/health` endpoint

---

## PYPROJECT.TOML DEPENDENCIES

Include at minimum:
- fastapi[standard]
- sqlmodel
- alembic
- celery[redis]
- redis
- minio
- python-jose[cryptography]
- passlib[bcrypt]
- python-multipart
- pydantic-settings
- python-magic (for file type validation)
- httpx (for tests)
- pytest, pytest-asyncio (dev)

---

## SECURITY REQUIREMENTS

- Validate uploaded file MIME type with python-magic (not just extension)
- Max file size enforced at nginx/FastAPI level (configurable via env)
- Files stored in MinIO with random UUID keys (never original filenames)
- ffmpeg/cwebp commands must NOT use shell=True (use list args, subprocess.run)
- Presigned URLs expire (configurable, default 3600s)
- Rate limiting via slowapi (leaky bucket per user)
- All secrets via environment variables, never hardcoded
- CORS configurable via env (ALLOWED_ORIGINS)

---

## CONFIGURATION (.env based)

All config via pydantic-settings BaseSettings. Generate a `.env.example` with:
- DATABASE_URL
- REDIS_URL  
- MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET
- SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
- MAX_UPLOAD_SIZE_MB (default 500)
- ALLOWED_ORIGINS
- CELERY_WORKERS (for documentation)

---

## SCALABILITY NOTES TO IMPLEMENT AS COMMENTS

- Worker scaling: `docker compose up --scale worker=4`
- Each worker should set ffmpeg `-threads` based on available CPUs (auto via os.cpu_count())
- MinIO can be swapped 1:1 for AWS S3 by changing env vars (boto3 compatible)
- PostgreSQL connection pooling via asyncpg + SQLAlchemy async engine
- Redis can be replaced with RabbitMQ by changing CELERY_BROKER_URL

---

## WHAT TO GENERATE

1. Complete folder structure with all files
2. `docker-compose.yml` and `docker-compose.override.yml`
3. `Dockerfile` (multi-stage)
4. `pyproject.toml` (UV format)
5. `alembic/env.py` configured for async SQLAlchemy
6. All `src/` files — complete, no placeholders, no "# implement this"
7. `.env.example`
8. `README.md` with: quickstart (3 commands), API usage examples with curl, 
   how to scale workers, how to add a new conversion endpoint (step-by-step)

Generate real, runnable code. Do not skip implementations.