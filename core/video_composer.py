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

# Must be even for libx264 (yuv420p)
MAX_W = 720
MAX_H = 1280
TARGET_FPS = 24


def _resample_filter():
    try:
        return Image.Resampling.LANCZOS
    except AttributeError:
        return getattr(Image, "LANCZOS", getattr(Image, "ANTIALIAS", 1))


def _resize_image(src: Path, dest: Path) -> Path:
    """Force exact MAX_W x MAX_H (both even) so libx264 never sees odd sizes."""
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
        ox = (MAX_W - nw) // 2
        oy = (MAX_H - nh) // 2
        canvas.paste(im, (ox, oy))

        dest.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(dest, "JPEG", quality=85, optimize=True)
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
        f"(total {audio.duration:.1f}s, {len(resized)} frames, {TARGET_FPS}fps, "
        f"{MAX_W}x{MAX_H})"
    )

    clips = []
    video = None
    try:
        for img in resized:
            clip = (
                ImageClip(str(img))
                .set_duration(duration_per_image)
                .resize(newsize=(MAX_W, MAX_H))
            )
            clips.append(clip)

        video = concatenate_videoclips(clips, method="compose")
        if video.w % 2 or video.h % 2:
            video = video.resize(newsize=(MAX_W, MAX_H))
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
