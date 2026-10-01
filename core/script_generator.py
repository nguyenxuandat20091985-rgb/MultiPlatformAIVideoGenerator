"""Script generation via Groq with a deterministic local fallback."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from groq import Groq

from config.settings import settings


def _local_script(topic: str, style: str, target_audience: str, cta: str) -> Dict[str, Any]:
    """Always-valid fallback so the factory can render a video without an LLM key."""
    lines = [
        f"Bạn có biết điều này về {topic}?",
        f"Hãy cùng tìm hiểu {topic} theo cách ngắn gọn và dễ hiểu.",
        f"Điểm đầu tiên: hãy tập trung vào điều quan trọng nhất của {topic}.",
        f"Điểm thứ hai: áp dụng từng bước nhỏ thay vì cố làm tất cả cùng lúc.",
        f"Điểm thứ ba: kiểm tra kết quả và điều chỉnh theo thực tế.",
        f"Với phong cách {style} dành cho {target_audience}, điều quan trọng là tính rõ ràng và dễ áp dụng.",
        f"Nếu bạn đang quan tâm đến {topic}, hãy lưu lại video này để xem lại.",
        cta or "Theo dõi để xem thêm các video hữu ích!",
    ]
    durations = [5, 6, 6, 6, 6, 7, 6, 5]
    scenes = [
        {
            "scene_number": i + 1,
            "visual_description": f"Vertical cinematic visual representing: {line}",
            "voiceover_text": line,
            "duration_seconds": durations[i],
        }
        for i, line in enumerate(lines)
    ]
    return {
        "script": " ".join(lines),
        "scenes": scenes,
        "total_duration": sum(durations),
        "generation_mode": "local_fallback",
    }


def generate_script(
    topic: str,
    style: str,
    target_audience: str,
    cta: str,
) -> Dict[str, Any]:
    """Generate an engaging short-form script; fall back locally if Groq is unavailable."""
    if not settings.GROQ_API_KEY:
        print("⚠️ GROQ_API_KEY not configured; using local script fallback.")
        return _local_script(topic, style, target_audience, cta)

    prompt = f"""
You are a creative assistant specialized in writing engaging and dynamic video scripts
for TikTok, YouTube Shorts, Instagram Reels and Facebook Reels.
Create a 45–60 second script about:
- Topic: {topic}
- Style: {style}
- Target Audience: {target_audience}
- CTA: {cta}

Return ONLY valid JSON:
{{
  "script": "Full script text",
  "scenes": [
    {{
      "scene_number": 1,
      "visual_description": "Detailed visual description",
      "voiceover_text": "Narration for this scene",
      "duration_seconds": 5
    }}
  ],
  "total_duration": 50
}}
Constraints: 8–14 scenes, concise language, strong first 3 seconds, CTA at the end.
"""

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
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
        if "scenes" not in data or not data["scenes"]:
            raise ValueError("Generated script has no scenes.")
        if "script" not in data:
            data["script"] = " ".join(s.get("voiceover_text", "") for s in data["scenes"])
        if "total_duration" not in data:
            data["total_duration"] = sum(int(s.get("duration_seconds", 4)) for s in data["scenes"])
        return data
    except Exception as exc:
        print(f"⚠️ Groq script generation failed ({exc}); using local fallback.")
        return _local_script(topic, style, target_audience, cta)


def save_script(script_data: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)
    print(f"✅ Script saved → {path}")
