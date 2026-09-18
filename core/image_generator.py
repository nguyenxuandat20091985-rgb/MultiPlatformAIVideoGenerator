"""Generate images via Together AI FLUX model."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import requests

from config.settings import settings


def generate_images(image_prompts_path: Path, output_dir: Path) -> None:
    """
    Generate one image per prompt using Together AI FLUX.1-schnell.
    Images are saved as 001.jpeg, 002.jpeg, ... in output_dir.
    """
    if not settings.TOGETHER_API_KEY:
        raise ValueError("TOGETHER_API_KEY is not set.")

    with open(image_prompts_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    prompts = data.get("prompts", [])
    if not prompts:
        raise ValueError("No prompts found.")

    output_dir.mkdir(parents=True, exist_ok=True)

    for i, prompt_data in enumerate(prompts, start=1):
        print(f"🌄 Generating image {i}/{len(prompts)}...")

        # Build a single rich prompt string
        parts = [
            prompt_data.get("subject", ""),
            ", ".join(prompt_data.get("artform", [])),
            f"shot with {prompt_data.get('device', ['camera'])[0]}" if prompt_data.get("device") else "",
            "style: " + ", ".join(prompt_data.get("photography_style", [])),
        ]
        scene = prompt_data.get("scene_details", {})
        if scene.get("lighting"):
            parts.append("lighting: " + ", ".join(scene["lighting"]))
        if scene.get("composition"):
            parts.append("composition: " + ", ".join(scene["composition"]))
        parts.append(prompt_data.get("additional_details", "vertical 9:16, high quality"))

        prompt_text = ", ".join(p for p in parts if p)

        response = requests.post(
            "https://api.together.xyz/v1/images/generations",
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "authorization": f"Bearer {settings.TOGETHER_API_KEY}",
            },
            json={
                "model": "black-forest-labs/FLUX.1-schnell",
                "prompt": prompt_text,
                "steps": 4,
                "n": 1,
                "height": 1792,
                "width": 1008,  # 9:16-ish
            },
            timeout=60,
        )

        if response.status_code != 200:
            print(f"⚠️  Image {i} failed: {response.status_code} – {response.text[:200]}")
            continue

        result = response.json()
        if not result.get("data"):
            print(f"⚠️  No image data for prompt {i}")
            continue

        image_url = result["data"][0].get("url")
        if not image_url:
            print(f"⚠️  Empty URL for prompt {i}")
            continue

        img_resp = requests.get(image_url, timeout=30)
        if img_resp.status_code == 200:
            image_path = output_dir / f"{i:03d}.jpeg"
            image_path.write_bytes(img_resp.content)
            print(f"✅ Saved {image_path}")
        else:
            print(f"⚠️  Download failed for image {i}")
