import os
import subprocess
import tempfile
from pathlib import Path

ALLOWED_VIDEO_MIMES = {
    "video/mp4",
    "video/webm",
    "video/x-matroska",
    "video/quicktime",
    "video/x-msvideo",
    "video/mpeg",
    "video/ogg",
    "video/3gpp",
}

# Each worker sets ffmpeg thread count based on available CPUs (auto-detected)
_THREADS = str(os.cpu_count() or 1)

_EXT_MAP = {"mp4": "mp4", "webm": "webm", "mkv": "mkv"}
_MIME_MAP = {"mp4": "video/mp4", "webm": "video/webm", "mkv": "video/x-matroska"}


def convert_video(
    data: bytes,
    output_format: str = "mp4",
    codec: str = "libx264",
    crf: int = 23,
    preset: str = "medium",
) -> tuple[bytes, str]:
    ext = _EXT_MAP.get(output_format, "mp4")
    mime = _MIME_MAP.get(output_format, "video/mp4")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input"
        output_path = Path(tmpdir) / f"output.{ext}"
        input_path.write_bytes(data)

        # shell=False intentional; args are validated from enum before reaching here
        cmd = [
            "ffmpeg",
            "-threads", _THREADS,
            "-i", str(input_path),
            "-c:v", codec,
            "-crf", str(crf),
            "-preset", preset,
            "-c:a", "aac",
            "-y",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=3600)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg convert failed: {result.stderr.decode()}")

        return output_path.read_bytes(), mime


def rotate_video(data: bytes, degrees: int, no_transcode: bool = False) -> bytes:
    _rotate_filter = {90: "transpose=1", 180: "transpose=2,transpose=2", 270: "transpose=2"}
    _meta_angle = {90: "90", 180: "180", 270: "270"}

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input"
        output_path = Path(tmpdir) / "output.mp4"
        input_path.write_bytes(data)

        if no_transcode:
            cmd = [
                "ffmpeg",
                "-i", str(input_path),
                "-c", "copy",
                "-metadata:s:v:0", f"rotate={_meta_angle.get(degrees, '90')}",
                "-y",
                str(output_path),
            ]
        else:
            cmd = [
                "ffmpeg",
                "-threads", _THREADS,
                "-i", str(input_path),
                "-vf", _rotate_filter.get(degrees, "transpose=1"),
                "-c:a", "copy",
                "-y",
                str(output_path),
            ]

        result = subprocess.run(cmd, capture_output=True, timeout=3600)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg rotate failed: {result.stderr.decode()}")

        return output_path.read_bytes()


def resize_video(data: bytes, width: int | None, height: int | None, keep_aspect: bool = True) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input"
        output_path = Path(tmpdir) / "output.mp4"
        input_path.write_bytes(data)

        if keep_aspect:
            vf = f"scale={width or -2}:{height or -2}"
        else:
            vf = f"scale={width or 'iw'}:{height or 'ih'}"

        cmd = [
            "ffmpeg",
            "-threads", _THREADS,
            "-i", str(input_path),
            "-vf", vf,
            "-c:a", "copy",
            "-y",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=3600)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg resize failed: {result.stderr.decode()}")

        return output_path.read_bytes()


def trim_video(data: bytes, start_time: str, end_time: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input"
        output_path = Path(tmpdir) / "output.mp4"
        input_path.write_bytes(data)

        cmd = [
            "ffmpeg",
            "-i", str(input_path),
            "-ss", start_time,
            "-to", end_time,
            "-c", "copy",
            "-y",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=3600)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg trim failed: {result.stderr.decode()}")

        return output_path.read_bytes()


def extract_thumbnail(data: bytes, timestamp: str = "00:00:01") -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input"
        output_path = Path(tmpdir) / "output.webp"
        input_path.write_bytes(data)

        cmd = [
            "ffmpeg",
            "-i", str(input_path),
            "-ss", timestamp,
            "-vframes", "1",
            "-c:v", "libwebp",
            "-y",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg thumbnail failed: {result.stderr.decode()}")

        return output_path.read_bytes()
