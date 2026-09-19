"""TTS audio generation – Kokoro primary, Edge-TTS fallback."""
from __future__ import annotations

import asyncio
import json
import subprocess
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


def _is_valid_audio(path: Path) -> bool:
    """Use ffprobe to reject HTML/JSON/partial files masquerading as MP3."""
    if not path.exists() or path.stat().st_size < 1024:
        return False
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "a:0",
                "-show_entries", "stream=codec_name,duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(path),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if result.returncode != 0 or len(lines) < 2:
            return False
        float(lines[-1])
        return True
    except (OSError, ValueError, subprocess.SubprocessError):
        return False


def _generate_silent_fallback(output_path: Path, duration: float = 10.0) -> None:
    """Last-resort valid MP3 so video composition can still complete."""
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-t", str(max(duration, 1.0)),
            "-c:a", "libmp3lame", "-b:a", "128k", str(output_path),
        ],
        check=True,
        timeout=30,
    )


def generate_audio(script_path: Path, audio_dir: Path) -> Path:
    """Generate a valid voiceover, validating every provider output before use."""
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    text = script.get("script") or " ".join(
        s.get("voiceover_text", "") for s in script.get("scenes", [])
    )
    if not text.strip():
        raise ValueError("No text found in script for TTS.")

    audio_dir.mkdir(parents=True, exist_ok=True)
    output_path = audio_dir / "voiceover.mp3"
    report_path = audio_dir / "audio_generation_report.json"
    attempts = []

    output_path.unlink(missing_ok=True)
    if _generate_kokoro(text, output_path) and _is_valid_audio(output_path):
        report = {"provider": "kokoro", "fallback_used": False, "valid": True}
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return output_path
    attempts.append("kokoro returned invalid/unreadable audio")
    output_path.unlink(missing_ok=True)

    success = asyncio.run(_generate_edge(text, output_path))
    if success and _is_valid_audio(output_path):
        report = {"provider": "edge-tts", "fallback_used": False, "valid": True}
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return output_path
    attempts.append("edge-tts returned invalid/unreadable audio")
    output_path.unlink(missing_ok=True)

    # Keep the video pipeline alive even if both remote TTS services are unavailable.
    _generate_silent_fallback(output_path)
    if not _is_valid_audio(output_path):
        raise RuntimeError("TTS providers failed and local audio fallback was invalid.")
    report = {
        "provider": "local-silence",
        "fallback_used": True,
        "valid": True,
        "reason": attempts,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("⚠️  Remote TTS failed; using valid local silent audio fallback.")
    return output_path
