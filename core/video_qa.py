"""Lightweight post-render quality gate.

Inspired by OpenMontage's contract/quality-gate approach, implemented
independently for this project so the API can reject broken MP4 files before
reporting a successful job.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def probe_video(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration:stream=codec_type,codec_name,width,height",
            "-of", "json", str(path),
        ],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")
    data = json.loads(result.stdout or "{}")
    streams = data.get("streams", [])
    duration = float(data.get("format", {}).get("duration") or 0)
    return {"duration": duration, "streams": streams}


def validate_final_video(path: Path) -> dict[str, Any]:
    info = probe_video(path)
    types = {s.get("codec_type") for s in info["streams"]}
    if info["duration"] <= 0:
        raise ValueError("Video duration is zero")
    if "video" not in types:
        raise ValueError("Video stream missing")
    report = {
        "valid": True,
        "duration": info["duration"],
        "has_video": "video" in types,
        "has_audio": "audio" in types,
        "path": str(path),
    }
    path.with_name("video_qa.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report
