"""Script generation via Groq (Llama models)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from groq import Groq

from config.settings import settings


def generate_script(
    topic: str,
    style: str,
    target_audience: str,
    cta: str,
) -> Dict[str, Any]:
    """
    Generate an engaging short-form video script using Groq Cloud API.
    Returns a dict with full script text, scenes, and total_duration.
    """
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set in environment.")

    client = Groq(api_key=settings.GROQ_API_KEY)

    prompt = f"""
You are a creative assistant specialized in writing engaging and dynamic video scripts
for TikTok, YouTube Shorts, Instagram Reels and Facebook Reels.
Your goal is to create scripts that maximize viewer retention.

The video must:
1. Capture attention in the first 3 seconds with a bold statement, intriguing question, or surprising fact.
2. Deliver concise, valuable, or entertaining content in the body using clear and energetic language.
3. Include a compelling call-to-action (CTA) in the last few seconds.

Create a video script based on:
- Topic: {topic}
- Style: {style}
- Target Audience: {target_audience}
- CTA: {cta}

Return ONLY valid JSON with this exact structure (no markdown, no extra text):
{{
  "script": "Full script text to be narrated by TTS",
  "scenes": [
    {{
      "scene_number": 1,
      "visual_description": "Detailed description of the visual for this scene",
      "voiceover_text": "Text to be narrated during this scene",
      "duration_seconds": 4
    }}
  ],
  "total_duration": 55
}}

Constraints:
- Aim for total_duration between 45 and 60 seconds.
- Create 8–14 scenes.
- Keep language snappy and suitable for short-form vertical video.
- The "script" field must be the concatenation of all voiceover_text fields.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a JSON-only script writer for short-form video."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.8,
        max_tokens=2048,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    data = json.loads(content)

    # Basic validation / defaults
    if "scenes" not in data or not data["scenes"]:
        raise ValueError("Generated script has no scenes.")
    if "script" not in data:
        data["script"] = " ".join(s.get("voiceover_text", "") for s in data["scenes"])
    if "total_duration" not in data:
        data["total_duration"] = sum(
            int(s.get("duration_seconds", 4)) for s in data["scenes"]
        )

    return data


def save_script(script_data: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)
    print(f"✅ Script saved → {path}")
