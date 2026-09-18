"""Compose final video from images + audio using MoviePy."""
from __future__ import annotations

from pathlib import Path

from moviepy.editor import (
    AudioFileClip,
    ImageClip,
    concatenate_videoclips,
)
from moviepy.video.fx.all import fadein, fadeout


def compose_video(
    images_dir: Path,
    audio_path: Path,
    output_path: Path,
    fade_duration: float = 0.4,
) -> Path:
    """
    Create a vertical video by sequencing images timed to the audio length.
    """
    image_files = sorted(images_dir.glob("*.jpeg")) + sorted(images_dir.glob("*.jpg"))
    if not image_files:
        raise ValueError(f"No images found in {images_dir}")

    audio = AudioFileClip(str(audio_path))
    duration_per_image = audio.duration / len(image_files)
    print(f"⏱️  Each image ≈ {duration_per_image:.2f}s (total {audio.duration:.1f}s)")

    clips = []
    for i, img in enumerate(image_files):
        clip = ImageClip(str(img)).set_duration(duration_per_image)
        # Optional gentle fades
        if i > 0:
            clip = fadein(clip, fade_duration)
        if i < len(image_files) - 1:
            clip = fadeout(clip, fade_duration)
        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose")
    video = video.set_audio(audio)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    video.write_videofile(
        str(output_path),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        logger=None,
    )
    video.close()
    audio.close()

    print(f"✅ Video composed → {output_path}")
    return output_path
