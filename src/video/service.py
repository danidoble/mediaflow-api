import json
import os
import subprocess
import tempfile
import time
from collections.abc import Callable
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

_FFMPEG_TIMEOUT = 3600

# WebM container only supports VP8/VP9/AV1 video + Vorbis/Opus audio.
# Auto-select sane defaults when the requested codec is incompatible.
_WEBM_ALLOWED_VIDEO = {"libvpx", "libvpx-vp9", "libaom-av1", "libsvtav1", "librav1e"}
_FORMAT_DEFAULT_CODEC = {"webm": "libvpx-vp9"}
_FORMAT_AUDIO = {"webm": "libopus"}
# Codecs that do NOT accept the -preset option (VP8, VP9, AV1 variants).
_NO_PRESET_CODECS = {"libvpx", "libvpx-vp9", "libaom-av1", "libsvtav1", "librav1e"}

# Per-codec extra speed/quality flags injected instead of -preset.
# libaom-av1 default cpu-used=1 is catastrophically slow; 6 is fast/usable.
# libvpx-vp9 benefits from -deadline good + cpu-used for reasonable speed.
_CODEC_EXTRA_ARGS: dict[str, list[str]] = {
    "libaom-av1": ["-cpu-used", "6", "-row-mt", "1"],
    "libsvtav1":  ["-preset", "8"],
    "librav1e":   ["-speed", "8"],
    "libvpx-vp9": ["-deadline", "good", "-cpu-used", "4", "-row-mt", "1"],
    "libvpx":     ["-deadline", "good", "-cpu-used", "4"],
}


def _get_video_duration(input_path: Path) -> float | None:
    """Return video duration in seconds via ffprobe, or None on failure."""
    try:
        r = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(input_path),
            ],
            capture_output=True,
            timeout=30,
        )
        if r.returncode == 0:
            info = json.loads(r.stdout.decode())
            dur = info.get("format", {}).get("duration")
            if dur:
                return float(dur)
    except Exception:
        pass
    return None


def convert_video(
    data: bytes,
    output_format: str = "mp4",
    codec: str = "libx264",
    crf: int = 23,
    preset: str = "medium",
    on_progress: Callable[[int], None] | None = None,
) -> tuple[bytes, str]:
    ext = _EXT_MAP.get(output_format, "mp4")
    mime = _MIME_MAP.get(output_format, "video/mp4")

    # Validate/correct codec for the target container.
    # WebM only accepts VP8/VP9/AV1; fall back to VP9 if an incompatible codec was requested.
    if output_format == "webm" and codec not in _WEBM_ALLOWED_VIDEO:
        codec = _FORMAT_DEFAULT_CODEC["webm"]

    audio_codec = _FORMAT_AUDIO.get(output_format, "aac")
    use_preset = codec not in _NO_PRESET_CODECS

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input"
        output_path = Path(tmpdir) / f"output.{ext}"
        progress_path = Path(tmpdir) / "ffprogress.txt"
        stderr_path = Path(tmpdir) / "ffstderr.txt"
        input_path.write_bytes(data)

        duration = _get_video_duration(input_path) if on_progress else None

        # shell=False intentional; args are validated/corrected above
        cmd = [
            "ffmpeg",
            "-threads", _THREADS,
            "-i", str(input_path),
            "-c:v", codec,
            "-crf", str(crf),
        ]
        if use_preset:
            cmd += ["-preset", preset]
        if codec in _CODEC_EXTRA_ARGS:
            cmd += _CODEC_EXTRA_ARGS[codec]
        cmd += ["-c:a", audio_codec]
        if on_progress and duration:
            cmd += ["-progress", str(progress_path), "-nostats"]
        cmd += ["-y", str(output_path)]

        if on_progress and duration:
            # stderr to a file to avoid the pipe buffer filling up and deadlocking
            # on long conversions (e.g. MKV/VP9 that produce verbose output).
            with open(stderr_path, "wb") as stderr_fh:
                proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=stderr_fh)
            last_pct = 0
            start = time.monotonic()
            while proc.poll() is None:
                if time.monotonic() - start > _FFMPEG_TIMEOUT:
                    proc.kill()
                    proc.wait()
                    raise RuntimeError("ffmpeg convert timed out")
                time.sleep(1)
                if progress_path.exists():
                    try:
                        for line in reversed(progress_path.read_text().splitlines()):
                            if line.startswith("out_time_ms="):
                                val = line.split("=", 1)[1].strip()
                                if val and val != "N/A":
                                    secs = int(val) / 1_000_000
                                    pct = min(int(secs / duration * 100), 99)
                                    if pct > last_pct:
                                        last_pct = pct
                                        on_progress(pct)
                                break
                    except Exception:
                        pass
            if proc.returncode != 0:
                stderr_msg = stderr_path.read_text(errors="replace") if stderr_path.exists() else ""
                raise RuntimeError(f"ffmpeg convert failed: {stderr_msg}")
        else:
            result = subprocess.run(cmd, capture_output=True, timeout=_FFMPEG_TIMEOUT)
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
