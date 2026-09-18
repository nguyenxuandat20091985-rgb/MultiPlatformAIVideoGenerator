"""Generate timed captions using OpenAI Whisper."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import whisper


def check_ffmpeg() -> bool:
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def generate_captions(audio_path: Path, captions_dir: Path) -> Path:
    """
    Transcribe audio with Whisper and save word-level / segment captions as JSON.
    """
    if not check_ffmpeg():
        raise RuntimeError(
            "FFmpeg is required for Whisper. Install it and ensure it is on PATH."
        )

    captions_dir.mkdir(parents=True, exist_ok=True)
    output_path = captions_dir / "captions.json"

    print("🔍 Loading Whisper model (base)...")
    model = whisper.load_model("base")

    print(f"🔍 Transcribing {audio_path}...")
    result = model.transcribe(str(audio_path), word_timestamps=True)

    segments: List[Dict[str, Any]] = []
    for seg in result.get("segments", []):
        entry = {
            "id": seg["id"],
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"].strip(),
        }
        if "words" in seg:
            entry["words"] = [
                {
                    "word": w["word"],
                    "start": round(w["start"], 2),
                    "end": round(w["end"], 2),
                }
                for w in seg["words"]
            ]
        segments.append(entry)

    data = {
        "language": result.get("language", "en"),
        "segments": segments,
        "full_text": result.get("text", "").strip(),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Captions saved → {output_path}")
    return output_path
