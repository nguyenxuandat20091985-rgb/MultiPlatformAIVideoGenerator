"""Generate images via Google's Gemini native image-generation API."""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from config.settings import settings


GEMINI_INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
IMAGE_MODEL = "gemini-3.1-flash-image"


def _extract_image_data(result: Dict[str, Any]) -> Optional[str]:
    """Return base64 image data from Gemini's convenience or step response."""
    output_image = result.get("output_image")
    if isinstance(output_image, dict) and output_image.get("data"):
        return output_image["data"]

    for step in result.get("steps", []) or []:
        for block in step.get("content", []) or []:
            if isinstance(block, dict) and block.get("type") == "image" and block.get("data"):
                return block["data"]

    return None


def _save_gemini_result(result: Dict[str, Any], image_path: Path) -> None:
    b64 = _extract_image_data(result)
    if not b64:
        raise RuntimeError(
            "Gemini returned no generated image data: "
            f"{json.dumps(result)[:1200]}"
        )
    try:
        image_path.write_bytes(base64.b64decode(b64))
    except Exception as exc:
        raise RuntimeError(f"Invalid Gemini base64 image response: {exc}") from exc


def _build_prompt(prompt_data: Dict[str, Any]) -> str:
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
    parts.append("Create a single vertical 9:16 image suitable for a short-form video.")
    return ", ".join(p for p in parts if p)


def generate_images(image_prompts_path: Path, output_dir: Path) -> None:
    """
    Generate one image per prompt with Gemini Nano Banana 2.
    Fails fast on authentication/API/response errors.
    """
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set.")

    with open(image_prompts_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    prompts = data.get("prompts", [])
    if not prompts:
        raise ValueError("No prompts found in image_prompts.json.")

    output_dir.mkdir(parents=True, exist_ok=True)

    for old in output_dir.iterdir():
        if old.is_file() and old.suffix.lower() in {".jpeg", ".jpg", ".png", ".webp"}:
            old.unlink()

    for i, prompt_data in enumerate(prompts, start=1):
        print(f"Generating Gemini image {i}/{len(prompts)}...")

        prompt_text = _build_prompt(prompt_data)

        try:
            response = requests.post(
                GEMINI_INTERACTIONS_URL,
                headers={
                    "x-goog-api-key": settings.GEMINI_API_KEY,
                    "content-type": "application/json",
                },
                json={
                    "model": IMAGE_MODEL,
                    "input": prompt_text,
                    "response_format": {
                        "type": "image",
                        "mime_type": "image/png",
                        "aspect_ratio": "9:16",
                        "image_size": "1K",
                    },
                },
                timeout=180,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Gemini image {i} request failed: {exc}") from exc

        if response.status_code != 200:
            detail = response.text[:1200].replace("\n", " ")
            raise RuntimeError(
                f"Image {i}/{len(prompts)} failed from Gemini API "
                f"(HTTP {response.status_code}): {detail}"
            )

        try:
            result = response.json()
        except ValueError as exc:
            raise RuntimeError(
                f"Gemini image {i}/{len(prompts)} returned invalid JSON: "
                f"{response.text[:600]}"
            ) from exc

        image_path = output_dir / f"{i:03d}.png"
        _save_gemini_result(result, image_path)

        if image_path.stat().st_size == 0:
            raise RuntimeError(f"Gemini image {i}/{len(prompts)} was saved but is empty.")

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
