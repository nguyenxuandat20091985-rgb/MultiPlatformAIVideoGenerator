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

    client = Groq(api_key=settings.GROQ_API_KEY)

    scene_descriptions = "\n".join(
        f"Scene {s['scene_number']}: {s.get('visual_description', s.get('voiceover_text', ''))}"
        for s in scenes
    )

    prompt = f"""
You are an expert prompt engineer for AI image models (FLUX / Stable Diffusion).
Given the following short-form video scenes, create one highly detailed image prompt per scene.

Scenes:
{scene_descriptions}

Return ONLY valid JSON:
{{
  "prompts": [
    {{
      "scene_number": 1,
      "subject": "main subject",
      "artform": ["cinematic photography", "digital art"],
      "device": ["Canon EOS R5"],
      "photography_style": ["dramatic lighting", "shallow depth of field"],
      "scene_details": {{
        "lighting": ["golden hour", "rim light"],
        "composition": ["rule of thirds", "centered subject"]
      }},
      "additional_details": "vertical 9:16 composition, high detail, vibrant colors, no text, no watermark"
    }}
  ]
}}

Rules:
- Exactly one prompt object per scene.
- Always emphasize vertical 9:16 framing suitable for mobile Shorts/Reels/TikTok.
- Avoid any text, logos or watermarks in the image description.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You output only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=3000,
        response_format={"type": "json_object"},
    )

    data = json.loads(response.choices[0].message.content)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ Image prompts saved → {output_path}")
    return data
