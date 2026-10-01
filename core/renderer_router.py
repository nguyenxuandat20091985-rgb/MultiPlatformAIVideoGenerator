"""Pluggable renderer router for the local video factory."""
from __future__ import annotations
import os
from pathlib import Path
from .video_composer import compose_video

def render_video(images_dir: Path, audio_path: Path, output_path: Path) -> Path:
    renderer = os.getenv("VIDEO_RENDERER", "ffmpeg").strip().lower()
    try:
        if renderer == "opencut":
            from .opencut_adapter import render_from_assets
            return render_from_assets(images_dir, audio_path, output_path)
        if renderer == "remotion":
            from .remotion_adapter import render_from_assets
            return render_from_assets(images_dir, audio_path, output_path)
    except Exception as exc:
        print(f"⚠️ {renderer} renderer unavailable: {exc}; falling back to FFmpeg.")
    return compose_video(images_dir, audio_path, output_path)
