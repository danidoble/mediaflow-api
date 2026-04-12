# MediaFlow API

Media conversion API for images and video. Accepts file uploads, processes them asynchronously via Celery workers using `ffmpeg` and `cwebp`, stores results in MinIO, and returns presigned download URLs.

## Quickstart

```bash
cp .env.example .env
docker compose build
docker compose up -d
```

The API is available at `http://localhost:8000`. OpenAPI docs at `http://localhost:8000/docs`.

Run database migrations:

```bash
docker compose exec -u root api alembic revision --autogenerate -m "initial"
docker compose exec -u root api alembic upgrade head
```

---

## API Usage

### Register & Login

```bash
# Register
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"strongpass"}' | jq .

# Login (returns access + refresh tokens)
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -F "username=user@example.com" -F "password=strongpass" | jq .

export TOKEN="<access_token from login>"
```

### Convert image to WebP

```bash
curl -s -X POST http://localhost:8000/api/v1/image/convert/webp \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@photo.jpg" \
  -F "quality=85" \
  -F "lossless=false" | jq .
# → {"success":true,"data":{"job_id":"...","status":"pending"},...}
```

### Convert image to AVIF

```bash
curl -s -X POST http://localhost:8000/api/v1/image/convert/avif \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@photo.png" \
  -F "quality=50" | jq .
```

### Convert image to any format (PNG, JPEG, GIF, BMP, TIFF, WebP, AVIF)

```bash
curl -s -X POST http://localhost:8000/api/v1/image/convert/format \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@photo.webp" \
  -F "output_format=png" \
  -F "quality=90" | jq .
```

Supported output formats: `png`, `jpg`/`jpeg`, `gif`, `bmp`, `tiff`/`tif`, `webp`, `avif`.

### Batch convert images to WebP

Send up to 20 files in a single request. One job is created per file.

```bash
curl -s -X POST http://localhost:8000/api/v1/image/batch/convert/webp \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@photo1.jpg" \
  -F "files=@photo2.png" \
  -F "files=@photo3.gif" \
  -F "quality=85" | jq .
# → {"success":true,"data":{"jobs":[{"job_id":"...","filename":"photo1.jpg","status":"pending"},...],"total":3},...}
```

### Batch convert images to AVIF

```bash
curl -s -X POST http://localhost:8000/api/v1/image/batch/convert/avif \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@photo1.jpg" \
  -F "files=@photo2.png" \
  -F "quality=50" | jq .
```

### Batch convert images to any format

```bash
curl -s -X POST http://localhost:8000/api/v1/image/batch/convert/format \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@photo1.webp" \
  -F "files=@photo2.avif" \
  -F "output_format=png" \
  -F "quality=90" | jq .
```

### Resize image

```bash
curl -s -X POST http://localhost:8000/api/v1/image/resize \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@photo.jpg" \
  -F "width=1280" \
  -F "height=720" \
  -F "fit=cover" | jq .
```

### Convert video

```bash
curl -s -X POST http://localhost:8000/api/v1/video/convert \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@video.mov" \
  -F "output_format=mp4" \
  -F "codec=libx264" \
  -F "crf=23" \
  -F "preset=medium" | jq .
```

### Trim video

```bash
curl -s -X POST http://localhost:8000/api/v1/video/trim \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@video.mp4" \
  -F "start_time=00:00:10" \
  -F "end_time=00:01:00" | jq .
```

### Extract thumbnail

```bash
curl -s -X POST http://localhost:8000/api/v1/video/thumbnail \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@video.mp4" \
  -F "timestamp=00:00:05" | jq .
```

### Poll job status / get result

```bash
JOB_ID="<job_id from above>"

curl -s http://localhost:8000/api/v1/jobs/$JOB_ID \
  -H "Authorization: Bearer $TOKEN" | jq .
# When status == "completed", data.result_url contains a 1-hour presigned download URL
```

### List your jobs

```bash
curl -s "http://localhost:8000/api/v1/jobs?page=1&page_size=10&status=completed" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

### Health check

```bash
curl -s http://localhost:8000/api/v1/health | jq .
```

---

## Scaling Workers

```bash
# Scale to 4 parallel workers (each runs ffmpeg with os.cpu_count() threads)
docker compose up --scale worker=4 -d
```

Each worker process auto-detects CPU count and passes `-threads N` to ffmpeg. Resource limits per worker container are set in `docker-compose.yml` under `worker.deploy.resources`.

---

## Token Refresh

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh_token>"}' | jq .
```

---

## Running Tests

```bash
# Install dev dependencies
uv sync

# Run tests (uses in-memory SQLite, no Docker needed)
pytest -v
```

---

## Adding a New Conversion Endpoint

1. **Define the Celery task** in `src/<domain>/tasks.py`:
   ```python
   @celery_app.task(bind=True, name="image.my_op", max_retries=3)
   def my_op_task(self, job_id, input_key, **kwargs): ...
   ```

2. **Implement the CLI call** in `src/<domain>/service.py` using `subprocess.run` with a list (no `shell=True`).

3. **Add the `JobType` enum value** in `src/jobs/models.py`.

4. **Register the route** in `src/<domain>/router.py`:
   ```python
   @router.post("/my-op", status_code=202)
   @limiter.limit("10/minute")
   async def my_op(request: Request, file: UploadFile = File(...), ...):
       data, mime = await _validate_upload(file, settings.max_upload_size_bytes)
       input_key = storage.upload_bytes(data, mime, prefix="uploads")
       job = await create_job(current_user.id, JobType.MY_OP, input_key, db)
       task = my_op_task.delay(str(job.id), input_key, ...)
       await update_job_status(job.id, job.status, db, celery_task_id=task.id)
       return {"success": True, "data": {"job_id": str(job.id), "status": "pending"}}
   ```

5. Run `alembic revision --autogenerate -m "add job type"` if you changed the DB schema.

---

## Architecture Notes

- **MinIO → AWS S3**: change `MINIO_ENDPOINT` to your S3 endpoint and update credentials. The MinIO Python SDK is S3-compatible.
- **Redis → RabbitMQ**: change `CELERY_BROKER_URL` to `amqp://user:pass@rabbitmq/vhost`.
- **PostgreSQL connection pooling**: handled by SQLAlchemy async engine (`pool_size=10`, `max_overflow=20`).
- **File security**: MIME type validated with `python-magic` (libmagic), not file extension. Files stored under random UUID keys in MinIO.
- **Presigned URLs**: expire after `PRESIGNED_URL_EXPIRE` seconds (default 3600).

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async PostgreSQL DSN |
| `REDIS_URL` | `redis://redis:6379/0` | Redis for health check |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/1` | Celery result backend |
| `MINIO_ENDPOINT` | `minio:9000` | MinIO/S3 endpoint |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key |
| `MINIO_BUCKET` | `mediaflow` | Default bucket |
| `SECRET_KEY` | — | JWT signing key (required in prod) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `MAX_UPLOAD_SIZE_MB` | `500` | Max upload size |
| `ALLOWED_ORIGINS` | `["*"]` | CORS origins |
| `PRESIGNED_URL_EXPIRE` | `3600` | Result URL TTL in seconds |
