"""Burn captions onto the video using MoviePy TextClips."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from moviepy.editor import (
    CompositeVideoClip,
    TextClip,
    VideoFileClip,
)


def add_captions_to_video(
    video_path: Path,
    captions_path: Path,
    output_path: Path,
    fontsize: int = 48,
    font: str = "DejaVu-Sans-Bold",
    color: str = "white",
    stroke_color: str = "black",
    stroke_width: int = 2,
) -> Path:
    """
    Overlay timed captions from Whisper JSON onto the video.
    Falls back to a simple full-text overlay if segments are missing.
    """
    with open(captions_path, "r", encoding="utf-8") as f:
        captions = json.load(f)

    video = VideoFileClip(str(video_path))
    segments = captions.get("segments", [])

    text_clips: List[TextClip] = []

    if segments:
        for seg in segments:
            txt = seg.get("text", "").strip()
            if not txt:
                continue
            start = float(seg["start"])
            end = float(seg["end"])
            duration = max(0.1, end - start)

            try:
                tc = (
                    TextClip(
                        txt,
                        fontsize=fontsize,
                        font=font,
                        color=color,
                        stroke_color=stroke_color,
                        stroke_width=stroke_width,
                        method="caption",
                        size=(video.w * 0.9, None),
                        align="center",
                    )
                    .set_position(("center", "bottom"))
                    .set_start(start)
                    .set_duration(duration)
                )
                text_clips.append(tc)
            except Exception as e:
                print(f"⚠️  Caption clip skipped: {e}")
    else:
        # Fallback: show full text in the middle for a few seconds
        full = captions.get("full_text", "")
        if full:
            tc = (
                TextClip(
                    full[:120] + ("..." if len(full) > 120 else ""),
                    fontsize=fontsize,
                    font=font,
                    color=color,
                    stroke_color=stroke_color,
                    stroke_width=stroke_width,
                    method="caption",
                    size=(video.w * 0.9, None),
                )
                .set_position("center")
                .set_duration(min(8, video.duration))
            )
            text_clips.append(tc)

    if text_clips:
        final = CompositeVideoClip([video] + text_clips)
    else:
        final = video

    output_path.parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(
        str(output_path),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        logger=None,
    )
    final.close()
    video.close()

    print(f"✅ Captioned video → {output_path}")
    return output_path
