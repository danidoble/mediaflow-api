## Behavior

Be concise. Do not explain what you are doing — just do it.
No reasoning blocks. No obvious inline comments. No unsolicited documentation.
Do not generate tests unless explicitly asked.
Respond in Spanish when talking; write all code and identifiers in English.

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

## PROJECT OVERVIEW

A RESTful API that accepts image and video files, processes them using CLI tools 
(cwebp, ffmpeg), and returns converted/manipulated results. Everything runs inside 
Docker Compose. No frontend needed — pure API consumed by web, mobile, or CLI clients.

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