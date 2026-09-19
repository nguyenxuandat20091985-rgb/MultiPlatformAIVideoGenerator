"""Compose final vertical video from images + audio using FFmpeg.

The composer intentionally uses FFmpeg's streaming pipeline instead of keeping all
MoviePy image frames in Python memory. This is safer on small Render instances.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


def _probe_duration(audio_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Unable to read audio duration: {result.stderr.strip()[-500:]}"
        )
    try:
        duration = float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError("Audio duration is invalid.") from exc
    if duration <= 0:
        raise RuntimeError("Audio duration must be greater than zero.")
    return duration


def _ffmpeg_concat_escape(path: Path) -> str:
    # concat demuxer uses single quotes; escape embedded quotes/backslashes.
    value = str(path.resolve()).replace("\\", "\\\\").replace("'", "'\\''")
    return f"'{value}'"


def compose_video(
    images_dir: Path,
    audio_path: Path,
    output_path: Path,
    fade_duration: float = 0.4,
) -> Path:
    """
    Create a vertical MP4 while streaming image frames through FFmpeg.

    The Render-safe profile is 720x1280/24fps with a single encoder thread.
    This intentionally trades some encoding quality/speed for predictable RAM
    usage on small instances and avoids worker crashes/502 responses.
    """
    del fade_duration

    image_files = sorted(
        [
            *images_dir.glob("*.jpeg"),
            *images_dir.glob("*.jpg"),
            *images_dir.glob("*.png"),
            *images_dir.glob("*.webp"),
        ]
    )
    if not image_files:
        raise ValueError(f"No images found in {images_dir}")

    duration = _probe_duration(audio_path)
    duration_per_image = duration / len(image_files)
    print(f"FFmpeg compose: {len(image_files)} images, ≈ {duration_per_image:.2f}s each, total {duration:.1f}s")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    concat_file = output_path.parent / "images.concat.txt"

    lines = []
    for image in image_files:
        lines.append(f"file {_ffmpeg_concat_escape(image)}")
        lines.append(f"duration {duration_per_image:.6f}")
    # concat requires the final file to be repeated for the final duration entry.
    lines.append(f"file {_ffmpeg_concat_escape(image_files[-1])}")
    concat_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-i", str(audio_path),
        "-vf", "scale=720:1280:force_original_aspect_ratio=decrease,"
               "pad=720:1280:(ow-iw)/2:(oh-ih)/2:color=black,"
               "format=yuv420p",
        "-map", "0:v:0", "-map", "1:a:0",
        "-t", f"{duration:.3f}",
        "-r", "24",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "stillimage",
        "-threads", "1",
        "-crf", "28",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        str(output_path),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=max(180, int(duration * 30) + 120),
        )
    except subprocess.TimeoutExpired as exc:
        output_path.unlink(missing_ok=True)
        raise RuntimeError("FFmpeg video composition timed out.") from exc
    finally:
        concat_file.unlink(missing_ok=True)

    if result.returncode != 0 or not output_path.exists() or output_path.stat().st_size < 10_000:
        output_path.unlink(missing_ok=True)
        detail = (result.stderr or result.stdout or "unknown FFmpeg error").strip()
        raise RuntimeError(f"FFmpeg composition failed: {detail[-1500:]}")

    print(f"Video composed → {output_path} ({output_path.stat().st_size} bytes)")
    return output_path
