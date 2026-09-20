"""Compose final video from images + audio — FFmpeg-first (low RAM)."""
from __future__ import annotations

from . import pillow_compat  # noqa: F401

import gc
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

MAX_W = 720
MAX_H = 1280
TARGET_FPS = 24


def _resample_filter():
    try:
        return Image.Resampling.LANCZOS
    except AttributeError:
        return getattr(Image, "LANCZOS", getattr(Image, "ANTIALIAS", 1))


def _resize_image(src: Path, dest: Path) -> Path:
    """Force exact even 720x1280 with letterbox."""
    with Image.open(src) as im:
        im = im.convert("RGB")
        w, h = im.size
        scale = min(MAX_W / w, MAX_H / h)
        nw = max(2, int(w * scale))
        nh = max(2, int(h * scale))
        nw -= nw % 2
        nh -= nh % 2
        im = im.resize((nw, nh), _resample_filter())
        canvas = Image.new("RGB", (MAX_W, MAX_H), (0, 0, 0))
        canvas.paste(im, ((MAX_W - nw) // 2, (MAX_H - nh) // 2))
        dest.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(dest, "JPEG", quality=85, optimize=True)
    return dest


def _probe_duration(audio_path: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        return max(0.5, float((r.stdout or "").strip()))
    except ValueError:
        return 15.0


def compose_video(
    images_dir: Path,
    audio_path: Path,
    output_path: Path,
    fade_duration: float = 0.25,
) -> Path:
    """Slideshow via FFmpeg only (no MoviePy encode — much less RAM)."""
    image_files = sorted(images_dir.glob("*.jpeg")) + sorted(images_dir.glob("*.jpg"))
    if not image_files:
        image_files = sorted(images_dir.glob("*.png"))
    if not image_files:
        raise ValueError(f"No images found in {images_dir}")

    work = images_dir / "_resized"
    work.mkdir(exist_ok=True)
    resized: list[Path] = []
    for i, img in enumerate(image_files):
        out = work / f"{i:03d}.jpg"
        try:
            resized.append(_resize_image(img, out))
        except Exception as e:
            print(f"⚠️  resize {img.name}: {e}")
            resized.append(img)

    duration = _probe_duration(audio_path)
    per = max(0.3, duration / len(resized))
    print(
        f"⏱️  FFmpeg slideshow: {len(resized)} frames × {per:.2f}s "
        f"(audio {duration:.1f}s) @ {MAX_W}x{MAX_H}"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        local_imgs = []
        for i, p in enumerate(resized):
            dest = td_path / f"f{i:03d}.jpg"
            shutil.copy2(p, dest)
            local_imgs.append(dest)

        list_file = td_path / "list.txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for p in local_imgs:
                f.write(f"file '{p.name}'\n")
                f.write(f"duration {per:.4f}\n")
            f.write(f"file '{local_imgs[-1].name}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-i", str(audio_path),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "stillimage",
            "-pix_fmt", "yuv420p",
            "-r", str(TARGET_FPS),
            "-c:a", "aac",
            "-b:a", "96k",
            "-shortest",
            "-movflags", "+faststart",
            str(output_path),
        ]
        print("▶️ ", " ".join(cmd[:8]), "...")
        proc = subprocess.run(cmd, cwd=str(td_path), capture_output=True, text=True)
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "")[-1500:]
            raise RuntimeError(f"FFmpeg compose failed ({proc.returncode}):\n{err}")

    gc.collect()
    if not output_path.exists() or output_path.stat().st_size < 1000:
        raise RuntimeError(f"Compose failed — empty output: {output_path}")

    print(f"✅ Video composed → {output_path} ({output_path.stat().st_size // 1024} KB)")
    return output_path
