"""Generate images with multi-key provider failover: OpenAI -> Gemini -> OpenRouter."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import re
from pathlib import Path
from typing import Any, Dict

import requests
from PIL import Image, ImageDraw, ImageOps

from config.settings import settings


OPENAI_IMAGES_URL = "https://api.openai.com/v1/images/generations"
OPENROUTER_IMAGES_URL = "https://openrouter.ai/api/v1/images"
GEMINI_INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


def _keys(raw: str, extras: list[str]) -> list[str]:
    values: list[str] = []
    for item in [raw, *extras]:
        for key in item.split(","):
            key = key.strip()
            if key and key not in values:
                values.append(key)
    return values


def _redact(text: str) -> str:
    """Never expose API keys or authorization material in UI/log errors."""
    text = str(text)
    patterns = [
        r"(sk-or-v1-[A-Za-z0-9_-]+)",
        r"(AIza[A-Za-z0-9_-]+)",
        r"(Bearer\s+)[A-Za-z0-9._~+/=-]+",
        r'''(x-goog-api-key["']?\s*[:=]\s*["']?)[^\s,"'}]+''',
        r'''(api[_-]?key["']?\s*[:=]\s*["']?)[^\s,"'}]+''',
    ]
    for pattern in patterns:
        text = re.sub(
            pattern,
            lambda m: (m.group(1) if m.lastindex else "") + "[REDACTED]",
            text,
            flags=re.IGNORECASE,
        )
    return text[:1800]


def _friendly_provider_error(provider: str, error_text: str) -> str:
    """Return a compact, safe message for common permanent provider failures."""
    safe = _redact(error_text)
    upper = safe.upper()
    if "HTTP 403" in upper and "CONSUMER_SUSPENDED" in upper:
        return f"{provider} HTTP 403 PERMISSION_DENIED/CONSUMER_SUSPENDED"
    if "HTTP 402" in upper and "INSUFFICIENT CREDITS" in upper:
        return f"{provider} HTTP 402 INSUFFICIENT_CREDITS"
    if "HTTP 401" in upper:
        return f"{provider} HTTP 401 UNAUTHORIZED"
    if "HTTP 404" in upper:
        return f"{provider} HTTP 404 NOT_FOUND"
    return safe


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


def _extract_openrouter_image_bytes(result: Dict[str, Any]) -> bytes:
    data = result.get("data")
    if not isinstance(data, list) or not data:
        raise RuntimeError("OpenRouter returned no image data.")

    first = data[0]
    if not isinstance(first, dict):
        raise RuntimeError("OpenRouter returned an invalid image item.")

    b64 = first.get("b64_json") or first.get("b64Json")
    if b64:
        return base64.b64decode(b64)

    image_url = first.get("url")
    if image_url:
        response = requests.get(image_url, timeout=60)
        response.raise_for_status()
        return response.content

    raise RuntimeError("OpenRouter response contained neither image data nor URL.")


def _extract_gemini_image_bytes(result: Dict[str, Any]) -> bytes:
    output_image = result.get("output_image")
    if isinstance(output_image, dict) and output_image.get("data"):
        return base64.b64decode(output_image["data"])

    for step in result.get("steps", []) or []:
        for block in step.get("content", []) or []:
            if (
                isinstance(block, dict)
                and block.get("type") == "image"
                and block.get("data")
            ):
                return base64.b64decode(block["data"])

    raise RuntimeError("Gemini returned no image data.")


def _normalize_to_png(image_bytes: bytes, image_path: Path) -> None:
    """Normalize every remote image to the encoder's low-memory canvas."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            image = image.convert("RGB")
            fitted = ImageOps.contain(image, (480, 854), method=Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (480, 854), "black")
            x = (480 - fitted.width) // 2
            y = (854 - fitted.height) // 2
            canvas.paste(fitted, (x, y))
            canvas.save(image_path, format="PNG", optimize=True)
    except Exception as exc:
        raise RuntimeError(f"Generated bytes are not a valid image: {exc}") from exc


def _generate_openai(prompt_text: str, api_key: str) -> bytes:
    response = requests.post(
        OPENAI_IMAGES_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.OPENAI_IMAGE_MODEL,
            "prompt": prompt_text,
            "size": settings.OPENAI_IMAGE_SIZE,
            "quality": settings.OPENAI_IMAGE_QUALITY,
            "n": 1,
        },
        timeout=180,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"OpenAI HTTP {response.status_code}: "
            f"{_redact(response.text)}"
        )
    try:
        result = response.json()
    except ValueError as exc:
        raise RuntimeError("OpenAI returned invalid JSON.") from exc
    data = result.get("data")
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        raise RuntimeError("OpenAI returned no image data.")
    b64 = data[0].get("b64_json") or data[0].get("b64Json")
    if not b64:
        raise RuntimeError("OpenAI response contained no base64 image data.")
    try:
        return base64.b64decode(b64)
    except Exception as exc:
        raise RuntimeError("OpenAI returned invalid base64 image data.") from exc


def _generate_openrouter(prompt_text: str, api_key: str) -> bytes:
    response = requests.post(
        OPENROUTER_IMAGES_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
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
    if response.status_code != 200:
        raise RuntimeError(
            f"OpenRouter HTTP {response.status_code}: "
            f"{_redact(response.text)}"
        )
    try:
        result = response.json()
    except ValueError as exc:
        raise RuntimeError("OpenRouter returned invalid JSON.") from exc
    return _extract_openrouter_image_bytes(result)


def _generate_gemini(prompt_text: str, api_key: str) -> bytes:
    response = requests.post(
        GEMINI_INTERACTIONS_URL,
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        },
        json={
            "model": settings.GEMINI_IMAGE_MODEL,
            "input": prompt_text,
            "response_format": {
                "type": "image",
                "mime_type": "image/png",
                "aspect_ratio": settings.GEMINI_IMAGE_ASPECT_RATIO,
                "image_size": settings.GEMINI_IMAGE_SIZE,
            },
        },
        timeout=180,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Gemini HTTP {response.status_code}: "
            f"{_redact(response.text)}"
        )
    try:
        result = response.json()
    except ValueError as exc:
        raise RuntimeError("Gemini returned invalid JSON.") from exc
    return _extract_gemini_image_bytes(result)


def _generate_local_fallback(prompt_text: str, image_path: Path, index: int) -> None:
    """Create a deterministic local visual so one provider outage cannot kill a video job.

    This is intentionally a visual fallback, not an AI-generated image. It uses only
    Pillow and the prompt hash to create a varied vertical background that the video
    composer can always consume when every remote image provider is unavailable.
    """
    seed = hashlib.sha256(f"{index}:{prompt_text}".encode("utf-8")).digest()
    width, height = 480, 854
    colors = [
        tuple(seed[i] for i in (0, 1, 2)),
        tuple(seed[i] for i in (8, 9, 10)),
        tuple(seed[i] for i in (16, 17, 18)),
    ]
    image = Image.new("RGB", (width, height), colors[0])
    draw = ImageDraw.Draw(image, "RGBA")

    # Smooth-enough vertical gradient made from inexpensive horizontal bands.
    bands = 48
    for band in range(bands):
        t = band / max(bands - 1, 1)
        if t < 0.5:
            a, b, local_t = colors[0], colors[1], t * 2
        else:
            a, b, local_t = colors[1], colors[2], (t - 0.5) * 2
        color = tuple(int(a[i] * (1 - local_t) + b[i] * local_t) for i in range(3))
        y0 = int(height * band / bands)
        y1 = int(height * (band + 1) / bands)
        draw.rectangle((0, y0, width, y1), fill=(*color, 255))

    # Large abstract shapes keep fallback frames visually useful without inventing
    # text or external assets. Positions/sizes are deterministic per prompt.
    x1 = 100 + seed[20] * 3
    y1 = 120 + seed[21] * 5
    r1 = 220 + seed[22] * 2
    x2 = 650 + seed[23] * 2
    y2 = 760 + seed[24] * 3
    r2 = 180 + seed[25] * 3
    x3 = 120 + seed[26] * 4
    y3 = 1370 + seed[27] * 2
    r3 = 260 + seed[28]
    draw.ellipse((x1 - r1, y1 - r1, x1 + r1, y1 + r1), fill=(*colors[2], 105))
    draw.ellipse((x2 - r2, y2 - r2, x2 + r2, y2 + r2), fill=(*colors[0], 125))
    draw.ellipse((x3 - r3, y3 - r3, x3 + r3, y3 + r3), fill=(*colors[1], 95))
    draw.polygon(
        [(0, height * 0.68), (width, height * 0.48), (width, height), (0, height)],
        fill=(*colors[0], 80),
    )
    image.save(image_path, format="PNG", optimize=True)


def generate_images(image_prompts_path: Path, output_dir: Path) -> dict[str, Any]:
    with open(image_prompts_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    prompts = data.get("prompts", [])
    if not prompts:
        raise ValueError("No prompts found in image_prompts.json.")

    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.iterdir():
        if old.is_file() and old.suffix.lower() in {".jpeg", ".jpg", ".png", ".webp"}:
            old.unlink()

    providers = settings.image_provider_order()
    provider_keys = {
        "openai": _keys(settings.OPENAI_API_KEY, settings.OPENAI_API_KEYS),
        "gemini": _keys(settings.GEMINI_API_KEY, settings.GEMINI_API_KEYS),
        "openrouter": _keys(
            settings.OPENROUTER_API_KEY, settings.OPENROUTER_API_KEYS
        ),
    }

    available = [
        p for p in providers
        if p in provider_keys and provider_keys[p]
    ]
    if not available:
        raise RuntimeError(
            "No image provider API key is configured. "
            "Set OPENAI_API_KEY, GEMINI_API_KEY, or "
            "OPENROUTER_API_KEY (including their _2/_3/_4 slots)."
        )

    generated = 0
    fallback_count = 0
    provider_failure_count = 0
    # Permanent authentication/credit failures should not be retried for every scene.
    # Transient failures (including rate limits) remain eligible for the next scene.
    disabled_keys: set[tuple[str, int]] = set()

    for i, prompt_data in enumerate(prompts, start=1):
        prompt_text = _build_prompt(prompt_data)
        saved = False
        errors: list[str] = []

        for provider in available:
            keys = provider_keys[provider]
            for key_index, api_key in enumerate(keys, start=1):
                if (provider, key_index) in disabled_keys:
                    continue
                try:
                    print(
                        f"Generating image {i}/{len(prompts)} with "
                        f"{provider} key #{key_index}..."
                    )
                    if provider == "openai":
                        image_bytes = _generate_openai(prompt_text, api_key)
                    elif provider == "gemini":
                        image_bytes = _generate_gemini(prompt_text, api_key)
                    elif provider == "openrouter":
                        image_bytes = _generate_openrouter(prompt_text, api_key)
                    else:
                        raise RuntimeError(f"Unsupported image provider: {provider}")

                    image_path = output_dir / f"{i:03d}.png"
                    _normalize_to_png(image_bytes, image_path)
                    if image_path.stat().st_size == 0:
                        raise RuntimeError("generated image is empty")

                    print(f"Saved {image_path} via {provider} key #{key_index}")
                    generated += 1
                    saved = True
                    break
                except Exception as exc:
                    provider_failure_count += 1
                    safe_error = _friendly_provider_error(provider, str(exc))
                    errors.append(
                        f"{provider} key #{key_index}: {safe_error}"
                    )
                    # 401/402/403/404 generally indicate a key/account/model
                    # configuration problem. Do not burn the same key on every scene.
                    match = re.search(r"HTTP\s+(401|402|403|404)\b", safe_error)
                    if match:
                        disabled_keys.add((provider, key_index))
                    print(
                        f"{provider} key #{key_index} failed for image {i}; "
                        "trying the next key/provider."
                    )
            if saved:
                break

        if not saved:
            summary = " | ".join(errors)
            image_path = output_dir / f"{i:03d}.png"
            try:
                _generate_local_fallback(prompt_text, image_path, i)
                if image_path.stat().st_size == 0:
                    raise RuntimeError("local fallback image is empty")
                generated += 1
                fallback_count += 1
                saved = True
                print(
                    f"Image {i}/{len(prompts)}: all remote image providers failed; "
                    "using local visual fallback so the video can continue."
                )
            except Exception as fallback_exc:
                raise RuntimeError(
                    f"Image {i}/{len(prompts)} failed even after local fallback. "
                    f"Provider errors: {summary}. "
                    f"Fallback error: {_redact(fallback_exc)}"
                ) from fallback_exc

    report = {
        "total": len(prompts),
        "generated": generated,
        "ai_generated": generated - fallback_count,
        "local_fallback": fallback_count,
        "provider_failures": provider_failure_count,
        "fallback_used": fallback_count > 0,
    }
    with open(output_dir / "image_generation_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report
