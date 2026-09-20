"""Compose final video from images + audio using MoviePy (low-RAM friendly)."""
from __future__ import annotations

from . import pillow_compat  # noqa: F401 — MoviePy + Pillow 10+

import gc
from pathlib import Path

from PIL import Image
from moviepy.editor import (
    AudioFileClip,
    ImageClip,
    concatenate_videoclips,
)

MAX_W = 720
MAX_H = 1280
TARGET_FPS = 24


def _resize_image(src: Path, dest: Path) -> Path:
    """Downscale to 9:16 max 720x1280 to cut memory during encode."""
    with Image.open(src) as im:
        im = im.convert("RGB")
        w, h = im.size
        scale = min(MAX_W / w, MAX_H / h, 1.0)
        nw, nh = int(w * scale), int(h * scale)
        nw -= nw % 2
        nh -= nh % 2
        if nw < 2 or nh < 2:
            nw, nh = MAX_W, MAX_H
        if (nw, nh) != (w, h):
            try:
                _resample = Image.Resampling.LANCZOS
            except AttributeError:
                _resample = getattr(Image, "LANCZOS", getattr(Image, "ANTIALIAS", 1))
            im = im.resize((nw, nh), _resample)
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, "JPEG", quality=85, optimize=True)
    return dest


def compose_video(
    images_dir: Path,
    audio_path: Path,
    output_path: Path,
    fade_duration: float = 0.25,
) -> Path:
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
            print(f"⚠️  resize {img.name}: {e} — using original")
            resized.append(img)

    audio = AudioFileClip(str(audio_path))
    duration_per_image = max(0.3, audio.duration / len(resized))
    print(
        f"⏱️  Each image ≈ {duration_per_image:.2f}s "
        f"(total {audio.duration:.1f}s, {len(resized)} frames, {TARGET_FPS}fps)"
    )

    clips = []
    video = None
    try:
        for img in resized:
            clip = (
                ImageClip(str(img))
                .set_duration(duration_per_image)
                .resize(height=MAX_H)
            )
            clips.append(clip)

        video = concatenate_videoclips(clips, method="compose")
        video = video.set_audio(audio)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        video.write_videofile(
            str(output_path),
            fps=TARGET_FPS,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            bitrate="1200k",
            audio_bitrate="96k",
            threads=2,
            logger=None,
            ffmpeg_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
        )
    finally:
        for c in clips:
            try:
                c.close()
            except Exception:
                pass
        try:
            if video is not None:
                video.close()
        except Exception:
            pass
        try:
            audio.close()
        except Exception:
            pass
        gc.collect()

    if not output_path.exists() or output_path.stat().st_size < 1000:
        raise RuntimeError(f"Compose failed — output missing or empty: {output_path}")

    print(f"✅ Video composed → {output_path} ({output_path.stat().st_size // 1024} KB)")
    return output_path
