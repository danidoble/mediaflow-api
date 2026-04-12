from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database — PostgreSQL via asyncpg; connection pooled by SQLAlchemy async engine
    database_url: str = "postgresql+asyncpg://mediaflow:mediaflow@db:5432/mediaflow"

    # Redis — swap CELERY_BROKER_URL for amqp:// to use RabbitMQ instead
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    # MinIO — swap endpoint + keys for AWS S3 (boto3/minio are S3-compatible)
    minio_endpoint: str = "minio:9000"
    # Public-facing endpoint used only for presigned URL generation.
    # Defaults to minio_endpoint when unset.
    # In development set to "localhost:<MINIO_API_PORT>" so URLs are
    # resolvable outside Docker. In production set to your CDN/domain.
    minio_public_endpoint: str = ""
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "mediaflow"
    minio_secure: bool = False
    minio_public_secure: bool = False
    presigned_url_expire: int = 3600

    @property
    def effective_public_endpoint(self) -> str:
        return self.minio_public_endpoint or self.minio_endpoint

    # JWT
    secret_key: str = "changeme-in-production-use-at-least-32-chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Upload limits
    max_upload_size_mb: int = 500

    # CORS
    allowed_origins: list[str] = ["*"]

    # App
    debug: bool = False

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
