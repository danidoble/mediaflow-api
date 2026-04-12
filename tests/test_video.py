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
async def test_convert_video_queued(client: AsyncClient):
    token = await _register_and_token(client, "vid_conv@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    with (
        patch("src.video.router.magic.from_buffer", return_value="video/mp4"),
        patch("src.storage.StorageService.upload_bytes", return_value="uploads/fake-key"),
        patch("src.video.tasks.convert_video_task.delay", return_value=MagicMock(id="task-v1")),
    ):
        response = await client.post(
            "/api/v1/video/convert",
            headers=headers,
            files={"file": ("test.mp4", b"\x00\x00\x00\x18ftyp" + b"\x00" * 50, "video/mp4")},
            data={"output_format": "mp4"},
        )

    assert response.status_code == 202
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "pending"


@pytest.mark.asyncio
async def test_rotate_video_queued(client: AsyncClient):
    token = await _register_and_token(client, "vid_rot@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    with (
        patch("src.video.router.magic.from_buffer", return_value="video/mp4"),
        patch("src.storage.StorageService.upload_bytes", return_value="uploads/fake-key"),
        patch("src.video.tasks.rotate_video_task.delay", return_value=MagicMock(id="task-v2")),
    ):
        response = await client.post(
            "/api/v1/video/rotate",
            headers=headers,
            files={"file": ("test.mp4", b"\x00\x00\x00\x18ftyp" + b"\x00" * 50, "video/mp4")},
            data={"degrees": "90"},
        )

    assert response.status_code == 202


@pytest.mark.asyncio
async def test_rotate_invalid_degrees(client: AsyncClient):
    token = await _register_and_token(client, "vid_rotbad@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    with (
        patch("src.video.router.magic.from_buffer", return_value="video/mp4"),
        patch("src.storage.StorageService.upload_bytes", return_value="uploads/fake-key"),
    ):
        response = await client.post(
            "/api/v1/video/rotate",
            headers=headers,
            files={"file": ("test.mp4", b"\x00\x00\x00\x18ftyp" + b"\x00" * 50, "video/mp4")},
            data={"degrees": "45"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_trim_video_queued(client: AsyncClient):
    token = await _register_and_token(client, "vid_trim@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    with (
        patch("src.video.router.magic.from_buffer", return_value="video/mp4"),
        patch("src.storage.StorageService.upload_bytes", return_value="uploads/fake-key"),
        patch("src.video.tasks.trim_video_task.delay", return_value=MagicMock(id="task-v3")),
    ):
        response = await client.post(
            "/api/v1/video/trim",
            headers=headers,
            files={"file": ("test.mp4", b"\x00\x00\x00\x18ftyp" + b"\x00" * 50, "video/mp4")},
            data={"start_time": "00:00:10", "end_time": "00:00:30"},
        )

    assert response.status_code == 202


@pytest.mark.asyncio
async def test_thumbnail_queued(client: AsyncClient):
    token = await _register_and_token(client, "vid_thumb@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    with (
        patch("src.video.router.magic.from_buffer", return_value="video/mp4"),
        patch("src.storage.StorageService.upload_bytes", return_value="uploads/fake-key"),
        patch("src.video.tasks.thumbnail_video_task.delay", return_value=MagicMock(id="task-v4")),
    ):
        response = await client.post(
            "/api/v1/video/thumbnail",
            headers=headers,
            files={"file": ("test.mp4", b"\x00\x00\x00\x18ftyp" + b"\x00" * 50, "video/mp4")},
            data={"timestamp": "00:00:05"},
        )

    assert response.status_code == 202


@pytest.mark.asyncio
async def test_unsupported_video_type(client: AsyncClient):
    token = await _register_and_token(client, "vid_bad@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    with (
        patch("src.video.router.magic.from_buffer", return_value="image/jpeg"),
        patch("src.storage.StorageService.upload_bytes", return_value="uploads/fake-key"),
    ):
        response = await client.post(
            "/api/v1/video/convert",
            headers=headers,
            files={"file": ("bad.jpg", b"\xff\xd8\xff", "image/jpeg")},
        )

    assert response.status_code == 415


@pytest.mark.asyncio
async def test_video_endpoint_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/v1/video/convert",
        files={"file": ("test.mp4", b"\x00", "video/mp4")},
    )
    assert response.status_code == 401
