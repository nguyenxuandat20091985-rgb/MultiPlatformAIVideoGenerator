"""Generate detailed image prompts from script scenes."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from groq import Groq

from config.settings import settings


def generate_image_prompts(script_path: Path, output_path: Path) -> Dict[str, Any]:
    """
    Read script.json and produce rich image generation prompts for each scene.
    """
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    scenes: List[Dict] = script.get("scenes", [])
    if not scenes:
        raise ValueError("No scenes found in script.")
    # Free-tier hosts: keep pipeline light
    MAX_SCENES = 5
    if len(scenes) > MAX_SCENES:
        scenes = scenes[:MAX_SCENES]

    scene_descriptions = "\n".join(
        f"Scene {s['scene_number']}: {s.get('visual_description', s.get('voiceover_text', ''))}"
        for s in scenes
    )

    prompt = f"""
You are an expert prompt engineer for AI image models (FLUX / Stable Diffusion).
Given the following short-form video scenes, create one highly detailed image prompt per scene.

Scenes:
{scene_descriptions}

Return ONLY valid JSON in this shape:
{{
  "prompts": [
    {{
      "scene_number": 1,
      "subject": "...",
      "artform": ["photography"],
      "device": ["camera"],
      "photography_style": ["cinematic"],
      "scene_details": {{
        "lighting": ["soft natural light"],
        "composition": ["centered, vertical 9:16"]
      }},
      "additional_details": "vertical 9:16, high quality, no text overlay"
    }}
  ]
}}
Rules:
- Exactly one prompt object per scene.
- Vertical 9:16 friendly composition.
- No on-image text or watermarks.
"""

    client = Groq(api_key=settings.GROQ_API_KEY)
    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    data = json.loads(content)

    # Cap prompts as well
    prompts = data.get("prompts", [])[:MAX_SCENES]
    data["prompts"] = prompts

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Image prompts saved → {output_path}")
    return data
