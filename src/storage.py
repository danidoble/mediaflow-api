import io
import uuid
from datetime import timedelta

from minio import Minio
from minio.error import S3Error

from src.config import settings


def _make_client(endpoint: str, secure: bool) -> Minio:
    return Minio(
        endpoint=endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=secure,
    )


class StorageService:
    def __init__(self) -> None:
        self._client = _make_client(settings.minio_endpoint, settings.minio_secure)
        # Separate client for presigned URL generation using the public endpoint.
        # AWS Sig V4 includes the Host header in the HMAC, so the client endpoint
        # must match what external clients will use in their requests.
        # We pre-seed _region_map to skip the HTTP bucket-region discovery that
        # would fail from inside Docker (public endpoint isn't reachable there).
        public = settings.effective_public_endpoint
        if public != settings.minio_endpoint:
            self._presign_client = _make_client(public, settings.minio_public_secure)
            self._presign_client._region_map[settings.minio_bucket] = "us-east-1"
        else:
            self._presign_client = self._client

    def ensure_bucket(self) -> None:
        if not self._client.bucket_exists(settings.minio_bucket):
            self._client.make_bucket(settings.minio_bucket)

    def upload_bytes(self, data: bytes, content_type: str, prefix: str = "") -> str:
        key = f"{prefix}/{uuid.uuid4()}" if prefix else str(uuid.uuid4())
        self._client.put_object(
            bucket_name=settings.minio_bucket,
            object_name=key,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return key

    def download_bytes(self, key: str) -> bytes:
        response = self._client.get_object(settings.minio_bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete_object(self, key: str) -> None:
        try:
            self._client.remove_object(settings.minio_bucket, key)
        except S3Error:
            pass

    def get_presigned_url(self, key: str, expires: int | None = None) -> str:
        expiry = timedelta(seconds=expires or settings.presigned_url_expire)
        return self._presign_client.presigned_get_object(
            bucket_name=settings.minio_bucket,
            object_name=key,
            expires=expiry,
        )

    def health_check(self) -> bool:
        try:
            self._client.list_buckets()
            return True
        except Exception:
            return False


storage = StorageService()
