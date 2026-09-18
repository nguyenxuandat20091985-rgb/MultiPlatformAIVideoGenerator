"""TTS audio generation – Kokoro primary, Edge-TTS fallback."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import edge_tts
import requests

from config.settings import settings


def _generate_kokoro(text: str, output_path: Path, voice: str = "am_michael") -> bool:
    try:
        resp = requests.post(
            "https://api.kokorotts.com/v1/audio/speech",
            json={
                "model": "kokoro",
                "input": text,
                "voice": voice,
                "response_format": "mp3",
                "speed": 1.0,
            },
            timeout=45,
        )
        if resp.status_code == 200:
            output_path.write_bytes(resp.content)
            print(f"✅ Audio generated with Kokoro TTS → {output_path}")
            return True
        print(f"⚠️  Kokoro error {resp.status_code}: {resp.text[:150]}")
        return False
    except Exception as e:
        print(f"⚠️  Kokoro failed: {e}")
        return False


async def _generate_edge(text: str, output_path: Path) -> bool:
    try:
        communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
        await communicate.save(str(output_path))
        print(f"✅ Audio generated with Edge-TTS → {output_path}")
        return True
    except Exception as e:
        print(f"⚠️  Edge-TTS failed: {e}")
        return False


def generate_audio(script_path: Path, audio_dir: Path) -> Path:
    """
    Generate voiceover.mp3 from the full script text.
    Tries Kokoro first, falls back to Edge-TTS.
    """
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    text = script.get("script") or " ".join(
        s.get("voiceover_text", "") for s in script.get("scenes", [])
    )
    if not text.strip():
        raise ValueError("No text found in script for TTS.")

    audio_dir.mkdir(parents=True, exist_ok=True)
    output_path = audio_dir / "voiceover.mp3"

    if not _generate_kokoro(text, output_path):
        success = asyncio.run(_generate_edge(text, output_path))
        if not success:
            raise RuntimeError("Both Kokoro and Edge-TTS failed to generate audio.")

    return output_path
