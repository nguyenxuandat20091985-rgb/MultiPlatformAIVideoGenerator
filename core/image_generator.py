"""Generate images through OpenRouter's unified Images API."""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from PIL import Image

from config.settings import settings


OPENROUTER_IMAGES_URL = "https://openrouter.ai/api/v1/images"


def _extract_image_bytes(result: Dict[str, Any]) -> bytes:
    """Extract generated image bytes from OpenRouter's buffered response."""
    data = result.get("data")
    if not isinstance(data, list) or not data:
        raise RuntimeError(
            "OpenRouter returned no image data: "
            f"{json.dumps(result)[:1600]}"
        )

    first = data[0]
    if not isinstance(first, dict):
        raise RuntimeError(f"OpenRouter returned an invalid image item: {first!r}")

    b64 = first.get("b64_json") or first.get("b64Json")
    if b64:
        try:
            return base64.b64decode(b64)
        except Exception as exc:
            raise RuntimeError(
                f"OpenRouter returned invalid base64 image data: {exc}"
            ) from exc

    image_url = first.get("url")
    if image_url:
        try:
            response = requests.get(image_url, timeout=60)
            response.raise_for_status()
            return response.content
        except requests.RequestException as exc:
            raise RuntimeError(
                f"OpenRouter image URL download failed: {exc}"
            ) from exc

    raise RuntimeError(
        "OpenRouter image response contained neither b64_json nor url: "
        f"{json.dumps(first)[:1000]}"
    )


def _save_as_png(image_bytes: bytes, image_path: Path) -> None:
    """Normalize provider output to PNG so the video composer has one stable format."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            image.convert("RGB").save(image_path, format="PNG")
    except Exception as exc:
        raise RuntimeError(
            f"OpenRouter returned bytes that are not a valid image: {exc}"
        ) from exc


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
    parts.append(
        "Create a single vertical 9:16 image suitable for a short-form video. "
        "Do not add text, logos, captions, borders, or watermarks."
    )
    return ", ".join(p for p in parts if p)


def generate_images(image_prompts_path: Path, output_dir: Path) -> None:
    """
    Generate one image per prompt through OpenRouter's dedicated Images API.
    Fails fast on authentication/API/response errors.
    """
    if not settings.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set.")

    with open(image_prompts_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    prompts = data.get("prompts", [])
    if not prompts:
        raise ValueError("No prompts found in image_prompts.json.")

    output_dir.mkdir(parents=True, exist_ok=True)

    # Remove stale images so an old successful job can never mask a failed generation.
    for old in output_dir.iterdir():
        if old.is_file() and old.suffix.lower() in {".jpeg", ".jpg", ".png", ".webp"}:
            old.unlink()

    for i, prompt_data in enumerate(prompts, start=1):
        print(
            f"Generating OpenRouter image {i}/{len(prompts)} "
            f"with {settings.OPENROUTER_IMAGE_MODEL}..."
        )

        prompt_text = _build_prompt(prompt_data)

        try:
            response = requests.post(
                OPENROUTER_IMAGES_URL,
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENROUTER_IMAGE_MODEL,
                    "prompt": prompt_text,
                    "aspect_ratio": settings.OPENROUTER_IMAGE_ASPECT_RATIO,
                    "n": 1,
                },
                timeout=180,
            )
        except requests.RequestException as exc:
            raise RuntimeError(
                f"OpenRouter image {i} request failed: {exc}"
            ) from exc

        if response.status_code != 200:
            detail = response.text[:1600].replace("\n", " ")
            raise RuntimeError(
                f"Image {i}/{len(prompts)} failed from OpenRouter "
                f"(HTTP {response.status_code}) using "
                f"{settings.OPENROUTER_IMAGE_MODEL}: {detail}"
            )

        try:
            result = response.json()
        except ValueError as exc:
            raise RuntimeError(
                f"OpenRouter image {i}/{len(prompts)} returned invalid JSON: "
                f"{response.text[:800]}"
            ) from exc

        image_bytes = _extract_image_bytes(result)
        image_path = output_dir / f"{i:03d}.png"
        _save_as_png(image_bytes, image_path)

        if image_path.stat().st_size == 0:
            raise RuntimeError(
                f"OpenRouter image {i}/{len(prompts)} was saved but is empty."
            )

        print(f"Saved {image_path}")

    created = sorted(
        p
        for p in output_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpeg", ".jpg", ".png", ".webp"}
    )
    if len(created) != len(prompts):
        raise RuntimeError(
            f"Image generation incomplete: created {len(created)} of "
            f"{len(prompts)} required images."
        )
