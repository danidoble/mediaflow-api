import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, patch


async def _register_and_token(client: AsyncClient, email: str) -> str:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass"},
    )
    return reg.json()["data"]["tokens"]["access_token"]


@pytest.mark.asyncio
async def test_convert_webp_queued(client: AsyncClient):
    token = await _register_and_token(client, "img_webp@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    with (
        patch("src.image.router.magic.from_buffer", return_value="image/jpeg"),
        patch("src.storage.StorageService.upload_bytes", return_value="uploads/fake-key"),
        patch("src.image.tasks.convert_to_webp_task.delay", return_value=MagicMock(id="task-1")),
    ):
        response = await client.post(
            "/api/v1/image/convert/webp",
            headers=headers,
            files={"file": ("test.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 50, "image/jpeg")},
            data={"quality": "80", "lossless": "false"},
        )

    assert response.status_code == 202
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "pending"
    assert "job_id" in body["data"]


@pytest.mark.asyncio
async def test_convert_avif_queued(client: AsyncClient):
    token = await _register_and_token(client, "img_avif@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    with (
        patch("src.image.router.magic.from_buffer", return_value="image/png"),
        patch("src.storage.StorageService.upload_bytes", return_value="uploads/fake-key"),
        patch("src.image.tasks.convert_to_avif_task.delay", return_value=MagicMock(id="task-2")),
    ):
        response = await client.post(
            "/api/v1/image/convert/avif",
            headers=headers,
            files={"file": ("test.png", b"\x89PNG\r\n" + b"\x00" * 50, "image/png")},
            data={"quality": "60"},
        )

    assert response.status_code == 202
    assert response.json()["data"]["status"] == "pending"


@pytest.mark.asyncio
async def test_resize_queued(client: AsyncClient):
    token = await _register_and_token(client, "img_resize@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    with (
        patch("src.image.router.magic.from_buffer", return_value="image/jpeg"),
        patch("src.storage.StorageService.upload_bytes", return_value="uploads/fake-key"),
        patch("src.image.tasks.resize_image_task.delay", return_value=MagicMock(id="task-3")),
    ):
        response = await client.post(
            "/api/v1/image/resize",
            headers=headers,
            files={"file": ("test.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 50, "image/jpeg")},
            data={"width": "800", "height": "600", "fit": "cover"},
        )

    assert response.status_code == 202


@pytest.mark.asyncio
async def test_unsupported_image_type(client: AsyncClient):
    token = await _register_and_token(client, "img_bad@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    with (
        patch("src.image.router.magic.from_buffer", return_value="application/zip"),
        patch("src.storage.StorageService.upload_bytes", return_value="uploads/fake-key"),
    ):
        response = await client.post(
            "/api/v1/image/convert/webp",
            headers=headers,
            files={"file": ("bad.zip", b"PK\x03\x04", "application/zip")},
            data={"quality": "80"},
        )

    assert response.status_code == 415


@pytest.mark.asyncio
async def test_image_endpoint_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/v1/image/convert/webp",
        files={"file": ("test.jpg", b"\xff\xd8", "image/jpeg")},
    )
    assert response.status_code == 401
