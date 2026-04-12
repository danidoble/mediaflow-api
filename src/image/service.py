import subprocess
import tempfile
from pathlib import Path

ALLOWED_IMAGE_MIMES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/tiff",
    "image/bmp",
}

_FORMAT_MIME: dict[str, str] = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "bmp": "image/bmp",
    "tiff": "image/tiff",
    "tif": "image/tiff",
    "webp": "image/webp",
    "avif": "image/avif",
}

ALLOWED_OUTPUT_FORMATS = set(_FORMAT_MIME.keys())


def convert_to_webp(data: bytes, quality: int = 80, lossless: bool = False) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input"
        output_path = Path(tmpdir) / "output.webp"
        input_path.write_bytes(data)

        cmd = ["cwebp"]
        if lossless:
            cmd.append("-lossless")
        else:
            cmd.extend(["-q", str(quality)])
        cmd.extend([str(input_path), "-o", str(output_path)])

        # shell=False is intentional — never pass user input through shell
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"cwebp failed: {result.stderr.decode()}")

        return output_path.read_bytes()


def convert_to_avif(data: bytes, quality: int = 60) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input"
        output_path = Path(tmpdir) / "output.avif"
        input_path.write_bytes(data)

        cmd = [
            "ffmpeg",
            "-i", str(input_path),
            "-c:v", "libaom-av1",
            "-crf", str(quality),
            "-b:v", "0",
            "-still-picture", "1",
            "-y",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=180)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg avif failed: {result.stderr.decode()}")

        return output_path.read_bytes()


def resize_image(data: bytes, width: int | None, height: int | None, fit: str = "cover") -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input"
        output_path = Path(tmpdir) / "output.webp"
        input_path.write_bytes(data)

        w = width or -2
        h = height or -2

        if fit == "fill":
            vf = f"scale={width or 'iw'}:{height or 'ih'}"
        elif fit == "contain":
            vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease"
        else:  # cover
            crop_w = width or "iw"
            crop_h = height or "ih"
            vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={crop_w}:{crop_h}"

        cmd = [
            "ffmpeg",
            "-i", str(input_path),
            "-vf", vf,
            "-y",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg resize failed: {result.stderr.decode()}")

        return output_path.read_bytes()


def convert_format(data: bytes, output_format: str, quality: int = 85) -> tuple[bytes, str]:
    """Convert image to any supported raster format using ffmpeg."""
    fmt = output_format.lower().lstrip(".")
    if fmt not in _FORMAT_MIME:
        raise ValueError(f"Unsupported output format: {fmt}")
    ext = "jpg" if fmt == "jpeg" else fmt
    mime = _FORMAT_MIME[fmt]

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input"
        output_path = Path(tmpdir) / f"output.{ext}"
        input_path.write_bytes(data)

        cmd = ["ffmpeg", "-i", str(input_path)]
        if fmt in ("jpg", "jpeg"):
            cmd.extend(["-q:v", str(max(2, 31 - quality // 4))])
        cmd.extend(["-y", str(output_path)])

        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg convert failed: {result.stderr.decode()}")

        return output_path.read_bytes(), mime
