"""Generate images via Together AI image models."""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Dict

import requests

from config.settings import settings


TOGETHER_IMAGES_URL = "https://api.together.ai/v1/images/generations"
IMAGE_MODEL = "Qwen/Qwen-Image-2.0"


def _save_image_result(item: Dict[str, Any], image_path: Path) -> None:
    """Save either a hosted image URL or a base64 image returned by Together."""
    image_url = item.get("url")
    if image_url:
        img_resp = requests.get(image_url, timeout=60)
        if img_resp.status_code != 200:
            raise RuntimeError(
                f"Image download failed ({img_resp.status_code}): "
                f"{img_resp.text[:300]}"
            )
        image_path.write_bytes(img_resp.content)
        return

    b64 = item.get("b64_json")
    if b64:
        try:
            image_path.write_bytes(base64.b64decode(b64))
        except Exception as exc:
            raise RuntimeError(f"Invalid base64 image response: {exc}") from exc
        return

    raise RuntimeError("Together returned no image URL or b64_json.")


def generate_images(image_prompts_path: Path, output_dir: Path) -> None:
    """
    Generate one image per prompt using a currently supported Together AI
    serverless image model. The pipeline fails fast if any required image
    cannot be generated, preventing a false-green images step.
    """
    if not settings.TOGETHER_API_KEY:
        raise ValueError("TOGETHER_API_KEY is not set.")

    with open(image_prompts_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    prompts = data.get("prompts", [])
    if not prompts:
        raise ValueError("No prompts found in image_prompts.json.")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Remove stale images from a previous retry.
    for old in output_dir.iterdir():
        if old.is_file() and old.suffix.lower() in {".jpeg", ".jpg", ".png", ".webp"}:
            old.unlink()

    for i, prompt_data in enumerate(prompts, start=1):
        print(f"Generating image {i}/{len(prompts)}...")

        parts = [
            prompt_data.get("subject", ""),
            ", ".join(prompt_data.get("artform", [])),
            (
                f"shot with {prompt_data.get('device', ['camera'])[0]}"
                if prompt_data.get("device")
                else ""
            ),
            "style: " + ", ".join(prompt_data.get("photography_style", [])),
        ]
        scene = prompt_data.get("scene_details", {})
        if scene.get("lighting"):
            parts.append("lighting: " + ", ".join(scene["lighting"]))
        if scene.get("composition"):
            parts.append("composition: " + ", ".join(scene["composition"]))
        parts.append(
            prompt_data.get(
                "additional_details",
                "vertical 9:16 composition, high quality, no text, no watermark",
            )
        )

        prompt_text = ", ".join(p for p in parts if p)

        try:
            response = requests.post(
                TOGETHER_IMAGES_URL,
                headers={
                    "accept": "application/json",
                    "content-type": "application/json",
                    "authorization": f"Bearer {settings.TOGETHER_API_KEY}",
                },
                json={
                    "model": IMAGE_MODEL,
                    "prompt": prompt_text,
                    "steps": 28,
                    "n": 1,
                    "width": 1008,
                    "height": 1792,
                    "response_format": "url",
                },
                timeout=180,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Image {i} request failed: {exc}") from exc

        if response.status_code != 200:
            detail = response.text[:800].replace("\n", " ")
            raise RuntimeError(
                f"Image {i}/{len(prompts)} failed from Together AI "
                f"(HTTP {response.status_code}): {detail}"
            )

        try:
            result = response.json()
        except ValueError as exc:
            raise RuntimeError(
                f"Image {i}/{len(prompts)} returned invalid JSON: "
                f"{response.text[:500]}"
            ) from exc

        items = result.get("data") or []
        if not items:
            raise RuntimeError(
                f"Image {i}/{len(prompts)} returned no data: "
                f"{json.dumps(result)[:800]}"
            )

        image_path = output_dir / f"{i:03d}.jpeg"
        _save_image_result(items[0], image_path)

        if image_path.stat().st_size == 0:
            raise RuntimeError(f"Image {i}/{len(prompts)} was saved but is empty.")

        print(f"Saved {image_path}")

    created = sorted(
        p for p in output_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpeg", ".jpg", ".png", ".webp"}
    )
    if len(created) != len(prompts):
        raise RuntimeError(
            f"Image generation incomplete: created {len(created)} of "
            f"{len(prompts)} required images."
        )
